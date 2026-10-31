#include <windows.h>
#include <oleauto.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

static const IID IID_IDISPATCH_LOCAL = {0x00020400, 0x0000, 0x0000, {0xC0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46}};

static void json_string(const wchar_t* value) {
    std::putchar('"');
    if (value) {
        for (const wchar_t* p = value; *p; ++p) {
            const unsigned int c = static_cast<unsigned int>(*p);
            if (c == '"' || c == '\\') { std::putchar('\\'); std::putchar(static_cast<int>(c)); }
            else if (c >= 0x20 && c < 0x7f) std::putchar(static_cast<int>(c));
            else std::printf("\\u%04x", c & 0xffff);
        }
    }
    std::putchar('"');
}

static void guid_text(REFGUID guid, wchar_t* out, size_t count) {
    StringFromGUID2(guid, out, static_cast<int>(count));
}

static void emit_typeinfo(ITypeInfo* info, unsigned int index) {
    TYPEATTR* attr = nullptr;
    if (FAILED(info->GetTypeAttr(&attr)) || !attr) {
        std::printf("{\"kind\":\"typeinfo_error\",\"index\":%u}\n", index);
        return;
    }
    wchar_t guid[64] = {};
    wchar_t* type_name = nullptr;
    BSTR doc = nullptr;
    guid_text(attr->guid, guid, sizeof(guid) / sizeof(guid[0]));
    info->GetDocumentation(MEMBERID_NIL, &type_name, &doc, nullptr, nullptr);
    std::printf("{\"kind\":\"interface\",\"index\":%u,\"guid\":", index);
    json_string(guid);
    std::printf(",\"typekind\":%u,\"functions\":%u,\"name\":", static_cast<unsigned int>(attr->typekind), attr->cFuncs);
    json_string(type_name);
    std::puts("}");

    for (UINT i = 0; i < attr->cFuncs; ++i) {
        FUNCDESC* fn = nullptr;
        if (FAILED(info->GetFuncDesc(i, &fn)) || !fn) continue;
        BSTR names[32] = {};
        UINT got = 0;
        info->GetNames(fn->memid, names, 32, &got);
        wchar_t* method_name = got ? names[0] : nullptr;
        std::printf("{\"kind\":\"method\",\"interface_index\":%u,\"ordinal\":%u,\"dispid\":%ld,\"invkind\":%u,\"params\":%u,\"optional\":%u,\"name\":",
                    index, i, static_cast<long>(fn->memid), static_cast<unsigned int>(fn->invkind),
                    static_cast<unsigned int>(fn->cParams), static_cast<unsigned int>(fn->cParamsOpt));
        json_string(method_name);
        std::printf(",\"param_vt\":[");
        for (SHORT p = 0; p < fn->cParams; ++p) {
            if (p) std::putchar(',');
            std::printf("%u", static_cast<unsigned int>(fn->lprgelemdescParam[p].tdesc.vt));
        }
        std::puts("]}");
        for (UINT n = 0; n < got; ++n) if (names[n]) SysFreeString(names[n]);
        info->ReleaseFuncDesc(fn);
    }
    if (type_name) SysFreeString(type_name);
    if (doc) SysFreeString(doc);
    info->ReleaseTypeAttr(attr);
}

int main(int argc, char** argv) {
    if (argc > 2) {
        std::fprintf(stderr, "Usage: mcvar_typeinfo_probe.exe [ProgID]\nDefault: MCVar.Var2\nThis probe only activates the COM class and reads ITypeInfo; it invokes no vendor methods.\n");
        return 2;
    }
    const char* progid = argc == 2 ? argv[1] : "MCVar.Var2";
    wchar_t wprogid[256] = {};
    if (MultiByteToWideChar(CP_ACP, 0, progid, -1, wprogid, 256) == 0) return 2;

    HRESULT hr = CoInitializeEx(nullptr, COINIT_APARTMENTTHREADED);
    if (FAILED(hr)) {
        std::printf("{\"kind\":\"error\",\"stage\":\"CoInitializeEx\",\"hresult\":\"0x%08lx\"}\n", static_cast<unsigned long>(hr));
        return 3;
    }
    CLSID clsid;
    hr = CLSIDFromProgID(wprogid, &clsid);
    if (FAILED(hr)) {
        std::printf("{\"kind\":\"error\",\"stage\":\"CLSIDFromProgID\",\"hresult\":\"0x%08lx\"}\n", static_cast<unsigned long>(hr));
        CoUninitialize();
        return 4;
    }
    IDispatch* dispatch = nullptr;
    hr = CoCreateInstance(clsid, nullptr, CLSCTX_INPROC_SERVER, IID_IDISPATCH_LOCAL, reinterpret_cast<void**>(&dispatch));
    if (FAILED(hr) || !dispatch) {
        std::printf("{\"kind\":\"error\",\"stage\":\"CoCreateInstance_IDispatch\",\"hresult\":\"0x%08lx\"}\n", static_cast<unsigned long>(hr));
        CoUninitialize();
        return 5;
    }
    UINT count = 0;
    hr = dispatch->GetTypeInfoCount(&count);
    if (FAILED(hr)) {
        std::printf("{\"kind\":\"error\",\"stage\":\"GetTypeInfoCount\",\"hresult\":\"0x%08lx\"}\n", static_cast<unsigned long>(hr));
        dispatch->Release(); CoUninitialize(); return 6;
    }
    std::printf("{\"kind\":\"probe\",\"progid\":\"%s\",\"typeinfo_count\":%u,\"hresult\":\"0x%08lx\"}\n", progid, count, static_cast<unsigned long>(hr));
    for (UINT i = 0; i < count; ++i) {
        ITypeInfo* info = nullptr;
        if (SUCCEEDED(dispatch->GetTypeInfo(i, LOCALE_USER_DEFAULT, &info)) && info) {
            emit_typeinfo(info, i);
            info->Release();
        }
    }
    dispatch->Release();
    CoUninitialize();
    return 0;
}
