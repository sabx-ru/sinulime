#include <windows.h>
#include <ddeml.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#pragma comment(lib, "user32.lib")

static HDDEDATA CALLBACK callback(UINT, UINT, HCONV, HSZ, HSZ, HDDEDATA, ULONG_PTR, ULONG_PTR) {
    return nullptr;
}

static void usage(const char* exe) {
    std::fprintf(stderr, "Usage: %s <service> <topic> <item> [item ...]\nMaximum 16 bounded XTYP_REQUEST reads; CF_TEXT only. No writes.\n", exe);
}

int main(int argc, char** argv) {
    if (argc < 4 || argc > 19) { usage(argv[0]); return 2; }
    DWORD instance = 0;
    UINT status = DdeInitializeA(&instance, callback, APPCMD_CLIENTONLY, 0);
    if (status != DMLERR_NO_ERROR) { std::fprintf(stderr, "DdeInitializeA: 0x%08X\n", status); return 3; }
    HSZ service = DdeCreateStringHandleA(instance, argv[1], CP_WINANSI);
    HSZ topic = DdeCreateStringHandleA(instance, argv[2], CP_WINANSI);
    HCONV conversation = DdeConnect(instance, service, topic, nullptr);
    if (!conversation) {
        std::fprintf(stderr, "DdeConnect failed: 0x%08X\n", DdeGetLastError(instance));
        DdeFreeStringHandle(instance, service); DdeFreeStringHandle(instance, topic);
        DdeUninitialize(instance); return 4;
    }
    int failures = 0;
    for (int i = 3; i < argc; ++i) {
        HSZ item = DdeCreateStringHandleA(instance, argv[i], CP_WINANSI);
        DWORD result = 0;
        HDDEDATA data = DdeClientTransaction(nullptr, 0, conversation, item, CF_TEXT,
                                              XTYP_REQUEST, 3000, &result);
        if (!data) {
            std::printf("READ item=%s result=FAIL error=0x%08X\n", argv[i], DdeGetLastError(instance));
            ++failures;
        } else {
            DWORD size = DdeGetData(data, nullptr, 0, 0);
            if (size > 4096) {
                std::printf("READ item=%s result=REJECT size=%lu bound=4096\n", argv[i], size);
                ++failures;
            } else {
                char buffer[4097] = {};
                DWORD copied = DdeGetData(data, reinterpret_cast<LPBYTE>(buffer), size, 0);
                std::printf("READ item=%s result=DATA bytes=%lu value=", argv[i], copied);
                for (DWORD j = 0; j < copied && buffer[j] != '\0'; ++j) {
                    unsigned char c = static_cast<unsigned char>(buffer[j]);
                    if (c >= 32 && c < 127) std::putchar(c); else std::printf("\\x%02X", c);
                }
                std::putchar('\n');
            }
            DdeFreeDataHandle(data);
        }
        DdeFreeStringHandle(instance, item);
    }
    DdeDisconnect(conversation);
    DdeFreeStringHandle(instance, service); DdeFreeStringHandle(instance, topic);
    DdeUninitialize(instance);
    return failures ? 1 : 0;
}
