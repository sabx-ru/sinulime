#define COBJMACROS
#include <windows.h>
#include <oleauto.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const wchar_t *LIBID_TEXT = L"{8F64C6E3-C2A4-11D2-BFCA-00609792C500}";
static const wchar_t *CLSID_TEXT = L"{8F64C6F2-C2A4-11D2-BFCA-00609792C500}";
static const wchar_t *TRACE_CLSID_TEXT = L"{DEB5BB92-C585-11D2-BFCF-000000000000}";
static void json(const char *kind, const char *name, const char *status, const char *detail) {
  printf("{\"kind\":\"%s\",\"name\":\"%s\",\"status\":\"%s\",\"detail\":\"%s\"}\n",kind,name,status,detail);
}
static void wjson(const char *kind, const wchar_t *name, const char *status, const char *detail) {
  char n[512]; int i=0;
  if(name) while(name[i] && i<500) { n[i]=(name[i]<128)?(char)name[i]:'?'; ++i; }
  n[i]=0; json(kind,n,status,detail);
}
static void wjson_wdetail(const char *kind, const wchar_t *name, const char *status, const wchar_t *detail) {
  char n[512]; char d[512]; int i=0;
  if(name) while(name[i] && i<500) { n[i]=(name[i]<128)?(char)name[i]:'?'; ++i; }
  n[i]=0; i=0;
  if(detail) while(detail[i] && i<500) { d[i]=(detail[i]<128)?(char)detail[i]:'?'; ++i; }
  d[i]=0; json(kind,n,status,d);
}
static int registry_key(const wchar_t *path) {
  HKEY key; LONG r=RegOpenKeyExW(HKEY_CLASSES_ROOT,path,0,KEY_READ,&key);
  if(r!=ERROR_SUCCESS) { wjson("registration",path,"missing","HKCR key unavailable"); return 0; }
  wchar_t value[512]; DWORD size=sizeof(value), type=0;
  r=RegQueryValueExW(key,NULL,NULL,&type,(BYTE*)value,&size);
  if(r==ERROR_SUCCESS && type==REG_SZ) wjson_wdetail("registration",path,"present",value);
  else wjson("registration",path,"present","default value unavailable");
  RegCloseKey(key); return 1;
}
static void inspect_registry(void) {
  wchar_t path[256];
  swprintf(path,256,L"TypeLib\\%s\\1.0\\0\\win32",LIBID_TEXT); registry_key(path);
  swprintf(path,256,L"CLSID\\%s\\InprocServer32",CLSID_TEXT); registry_key(path);
  swprintf(path,256,L"CLSID\\%s\\InprocServer32",TRACE_CLSID_TEXT); registry_key(path);
}
static void inspect_typelib(const wchar_t *path) {
  ITypeLib *lib=NULL; HRESULT hr=LoadTypeLibEx(path,REGKIND_NONE,&lib);
  if(FAILED(hr)) { json("typelib","LoadTypeLibEx","failed","offline resource load failed; see HRESULT"); printf("{\"kind\":\"hresult\",\"value\":\"0x%08lx\"}\n",(unsigned long)hr); return; }
  TLIBATTR *attr=NULL; if(SUCCEEDED(ITypeLib_GetLibAttr(lib,&attr))) {
    char guid[64]; snprintf(guid,sizeof(guid),"{%08lx-%04x-%04x-...}",(unsigned long)attr->guid.Data1,attr->guid.Data2,attr->guid.Data3);
    json("typelib","identity","loaded",guid); ITypeLib_ReleaseTLibAttr(lib,attr);
  }
  UINT count=ITypeLib_GetTypeInfoCount(lib);
  for(UINT i=0;i<count;i++) {
    ITypeInfo *ti=NULL; TYPEATTR *ta=NULL; BSTR tn=NULL;
    if(FAILED(ITypeLib_GetTypeInfo(lib,i,&ti))) continue;
    if(SUCCEEDED(ITypeInfo_GetTypeAttr(ti,&ta))) {
      ITypeInfo_GetDocumentation(ti,MEMBERID_NIL,&tn,NULL,NULL,NULL);
      wjson("type",tn?tn:L"(unnamed)","enumerated","TypeInfo from embedded resource");
      if(tn) { SysFreeString(tn); tn=NULL; }
      for(UINT f=0;f<ta->cFuncs;f++) { FUNCDESC *fd=NULL; if(SUCCEEDED(ITypeInfo_GetFuncDesc(ti,f,&fd))) {
        ITypeInfo_GetDocumentation(ti,fd->memid,&tn,NULL,NULL,NULL);
        wjson("member",tn?tn:L"(unnamed)","metadata_only","signature intentionally not invoked");
        if(tn) { SysFreeString(tn); tn=NULL; } ITypeInfo_ReleaseFuncDesc(ti,fd);
      }} ITypeInfo_ReleaseTypeAttr(ti,ta);
    }
    ITypeInfo_Release(ti);
  }
  ITypeLib_Release(lib);
}
static void gaps(void) {
  json("capability_gap","COM activation","not_attempted","Diagnostic does not instantiate target objects");
  json("capability_gap","ReadVarAsync","blocked","Exact ABI and parameter contract unresolved; no invocation compiled");
  json("capability_gap","ReadVarCyclic","blocked","Exact ABI, callback and lifecycle contract unresolved; no invocation compiled");
  json("capability_gap","connection_points","not_probed","No Advise or callback registration attempted");
}
int wmain(int argc, wchar_t **argv) {
  HRESULT hr=CoInitializeEx(NULL,COINIT_APARTMENTTHREADED);
  json("run","stage15_native_x86","started","registration and TypeInfo inspection only");
  inspect_registry();
  if(argc>1) inspect_typelib(argv[1]);
  else json("typelib","resource","not_loaded","Pass a DLL/OCX path to inspect its embedded TypeLib without registration");
  gaps();
  if(SUCCEEDED(hr)) CoUninitialize();
  return 0;
}
