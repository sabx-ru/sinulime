/*
 * NCDDE one-shot read-only diagnostic for Siemens SINUMERIK 840D / WinXP x86.
 * Based on the DDEML request pattern proven in the archived PCU test code.
 * ONE XTYP_REQUEST per invocation. NO POKE / EXECUTE / ADVISE / writes.
 * A successful DDE response proves only that the server answered the item.
 * It does NOT verify semantic type, axis binding, or drive safety.
 * Build with i686-w64-mingw32-gcc (Win32 runtime; XP subsystem 5.01).
 */
#ifndef WINVER
#define WINVER 0x0501
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0501
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <ddeml.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#define MAX_ITEM 220
#define MAX_REPLY 8192UL

static FILE *g_log = NULL;
static DWORD g_instance = 0;

static HDDEDATA CALLBACK dde_callback(UINT type, UINT fmt, HCONV conv,
                                      HSZ h1, HSZ h2, HDDEDATA data,
                                      ULONG_PTR a, ULONG_PTR b) {
    (void)type; (void)fmt; (void)conv; (void)h1; (void)h2;
    (void)data; (void)a; (void)b;
    return (HDDEDATA)0;
}

static void out(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vfprintf(stdout, fmt, ap);
    va_end(ap);
    fflush(stdout);
    if (g_log) {
        va_start(ap, fmt);
        vfprintf(g_log, fmt, ap);
        va_end(ap);
        fflush(g_log);
    }
}

static void trim(char *s) {
    size_t n;
    char *p=s;
    while (*p == ' ' || *p == '\t') ++p;
    if (p != s) memmove(s,p,strlen(p)+1);
    n=strlen(s);
    while (n && (s[n-1]=='\r' || s[n-1]=='\n' || s[n-1]==' ' || s[n-1]=='\t'))
        s[--n]='\0';
}

/* Fail closed if a set accidentally contains multiple enabled paths. */
static int read_item_file(const char *filename,char item[MAX_ITEM+1]) {
    FILE *f=fopen(filename,"rb");
    char line[1024]; int count=0,lineno=0;
    if (!f) { fprintf(stderr,"ERROR open items: %s\n",filename); return 0; }
    item[0]='\0';
    while (fgets(line,sizeof(line),f)) {
        size_t i,n;
        lineno++;
        if (!strchr(line,'\n') && !feof(f)) {
            fprintf(stderr,"ERROR items line %d too long\n",lineno);
            fclose(f);return 0;
        }
        trim(line);
        if (!line[0] || line[0]=='#' || line[0]==';') continue;
        n=strlen(line);
        if (count || n>MAX_ITEM || line[0]!='/' || n<3) {
            fprintf(stderr,"ERROR: expected exactly one valid /item in %s (line %d)\n",filename,lineno);
            fclose(f);return 0;
        }
        for(i=0;i<n;i++) {
            unsigned char ch=(unsigned char)line[i];
            if (ch<33 || ch>126 || ch=='"' || ch=='\'' || ch==';') {
                fprintf(stderr,"ERROR: invalid character in item line %d\n",lineno);
                fclose(f);return 0;
            }
        }
        strcpy(item,line);count++;
    }
    fclose(f);
    if(count!=1) {fprintf(stderr,"ERROR: no enabled item in %s\n",filename);return 0;}
    return 1;
}

static int safe_label(const char *s) {
    size_t i,n=strlen(s);
    if (!n || n>32) return 0;
    for(i=0;i<n;i++) {
        char c=s[i];
        if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
              (c>='0'&&c<='9')||c=='_'||c=='-')) return 0;
    }
    return 1;
}

static unsigned long le32(const unsigned char *p) {
    return (unsigned long)p[0] | ((unsigned long)p[1]<<8) |
           ((unsigned long)p[2]<<16) | ((unsigned long)p[3]<<24);
}

static int open_log(const char *label) {
    SYSTEMTIME t; char path[MAX_PATH];
    GetLocalTime(&t);
    if (!CreateDirectoryA("logs",NULL) && GetLastError()!=ERROR_ALREADY_EXISTS) {
        fprintf(stderr,"ERROR: cannot create logs directory\n");return 0;
    }
    _snprintf(path,sizeof(path)-1,
              "logs\\%s_%04u%02u%02u_%02u%02u%02u_%lu.txt",
              label,(unsigned)t.wYear,(unsigned)t.wMonth,(unsigned)t.wDay,
              (unsigned)t.wHour,(unsigned)t.wMinute,(unsigned)t.wSecond,
              (unsigned long)GetCurrentProcessId());
    path[sizeof(path)-1]='\0';
    g_log=fopen(path,"wb");
    if (!g_log) { fprintf(stderr,"ERROR open log %s\n",path);return 0; }
    out("LOG=%s\n",path);return 1;
}

static void dump_hex(const unsigned char *buf,DWORD size) {
    static const char digits[]="0123456789ABCDEF";
    char *hex=(char*)malloc((size_t)size*2+1);
    DWORD i;
    if(!hex) {out("HEX=OMITTED_NO_MEMORY\n");return;}
    for(i=0;i<size;i++) {
        hex[i*2]=digits[buf[i]>>4];
        hex[i*2+1]=digits[buf[i]&15];
    }
    hex[size*2]='\0';
    out("HEX=%s\n",hex);
    free(hex);
}

static void decode_frame(const unsigned char *buf,DWORD n,const char *format) {
    unsigned hlen,ver;unsigned long payload_len;double candidate;
    if(strcmp(format,"binary")!=0) {
        DWORD i;out("TEXT_ESCAPED=");
        for (i=0;i<n;i++) {
            unsigned char c=buf[i];
            if (c==0) break;
            if (c>=32 && c<=126 && c!='\\') out("%c",c);
            else out("\\x%02X",(unsigned)c);
        }
        out("\n");return;
    }
    if(n<20) {out("FRAME=SHORT length=%lu\n",(unsigned long)n);return;}
    hlen=(unsigned)buf[0] | ((unsigned)buf[1]<<8);
    ver=(unsigned)buf[2] | ((unsigned)buf[3]<<8);
    payload_len=le32(buf+12);
    out("FRAME=header_len:%u version:%u payload_len:%lu marker:%s\n",
        hlen,ver,payload_len,
        (buf[16]==0xF9 && buf[17]==0xF8 && buf[18]==0xF7 && buf[19]==0xF6)?"F9F8F7F6":"UNKNOWN");
    if (hlen!=20 || buf[16]!=0xF9 || buf[17]!=0xF8 ||
        buf[18]!=0xF7 || buf[19]!=0xF6 || payload_len>(unsigned long)(n-20)) {
        out("PAYLOAD=NOT_DECODED (unknown framing or invalid size)\n");return;
    }
    if(payload_len>=4) {
        unsigned long raw=le32(buf+20);
        out("CANDIDATE_INT32=%ld unsigned=%lu (NOT_CONFIRMED_TYPE)\n",
            (long)raw,raw);
    }
    if(payload_len>=8) {
        memcpy(&candidate,buf+20,8);
        out("CANDIDATE_DOUBLE=%.12g (NOT_CONFIRMED_TYPE)\n",candidate);
    }
}

static void usage(void) {
    fprintf(stderr,"Usage: ncdde_md_probe.exe --items=sets\\NAME.txt --label=NAME [--topic=machineswitch] [--format=binary|text] [--timeout=3000]\n");
    fprintf(stderr,"Exactly one read request. No write or subscription operations.\n");
}

int main(int argc,char **argv) {
    const char *items=NULL,*label="TEST",*topic="machineswitch",*fmt="binary";
    char item[MAX_ITEM+1];
    int i,timeout=3000,rc=1;
    UINT format;HSZ h_service=0,h_topic=0,h_item=0;HCONV conv=0;
    HDDEDATA data=0;DWORD dde_result=0,bytes=0,got=0;
    unsigned char *buf=NULL;
    DWORD start;
    SYSTEMTIME st;
    for(i=1;i<argc;i++) {
        if(strncmp(argv[i],"--items=",8)==0) items=argv[i]+8;
        else if(strncmp(argv[i],"--label=",8)==0) label=argv[i]+8;
        else if(strncmp(argv[i],"--topic=",8)==0) topic=argv[i]+8;
        else if(strncmp(argv[i],"--format=",9)==0) fmt=argv[i]+9;
        else if(strncmp(argv[i],"--timeout=",10)==0) timeout=atoi(argv[i]+10);
        else {usage();return 2;}
    }
    if (!items || !*items || !safe_label(label) || strlen(topic)>70 || !*topic ||
        (strcmp(fmt,"binary")!=0 && strcmp(fmt,"text")!=0) || timeout<100 || timeout>5000) {
        usage();return 2;
    }
    if(!read_item_file(items,item)) return 2;
    if(!open_log(label)) return 2;
    GetLocalTime(&st);
    out("DATE=%04u-%02u-%02u %02u:%02u:%02u.%03u\n",(unsigned)st.wYear,
        (unsigned)st.wMonth,(unsigned)st.wDay,(unsigned)st.wHour,
        (unsigned)st.wMinute,(unsigned)st.wSecond,(unsigned)st.wMilliseconds);
    out("MODE=READ_ONLY requests=1\nSERVICE=ncdde TOPIC=%s FORMAT=%s TIMEOUT_MS=%d\nITEM=%s\n",
        topic,fmt,timeout,item);
    if(DdeInitializeA(&g_instance,dde_callback,APPCMD_CLIENTONLY,0)!=DMLERR_NO_ERROR) {
        out("ERROR=DdeInitializeA failed\n");goto end;
    }
    h_service=DdeCreateStringHandleA(g_instance,"ncdde",CP_WINANSI);
    h_topic=DdeCreateStringHandleA(g_instance,topic,CP_WINANSI);
    h_item=DdeCreateStringHandleA(g_instance,item,CP_WINANSI);
    if(!h_service || !h_topic || !h_item) {out("ERROR=DdeCreateStringHandleA 0x%04X\n",DdeGetLastError(g_instance));goto end;}
    conv=DdeConnect(g_instance,h_service,h_topic,NULL);
    if(!conv) {out("ERROR=DdeConnect 0x%04X\n",DdeGetLastError(g_instance));goto end;}
    out("CONNECTED=YES\n");
    format=(strcmp(fmt,"binary")==0)?RegisterClipboardFormatA("ncddeBinary"):CF_TEXT;
    if(!format) {out("ERROR=RegisterClipboardFormatA\n");goto end;}
    start=GetTickCount();
    data=DdeClientTransaction(NULL,0,conv,h_item,format,XTYP_REQUEST,(DWORD)timeout,&dde_result);
    if(!data) {
        out("RESULT=REQUEST_FAILED error=0x%04X transaction=0x%08lX elapsed_ms=%lu\n",
            DdeGetLastError(g_instance),(unsigned long)dde_result,
            (unsigned long)(GetTickCount()-start));
        goto end;
    }
    bytes=DdeGetData(data,NULL,0,0);
    out("RESULT=DATA_HANDLE length=%lu elapsed_ms=%lu\n",
        (unsigned long)bytes,(unsigned long)(GetTickCount()-start));
    if(bytes==0 || bytes>MAX_REPLY) {out("ERROR=REPLY_SIZE_OUT_OF_BOUNDS limit=%lu\n",(unsigned long)MAX_REPLY);goto end;}
    buf=(unsigned char*)malloc(bytes);
    if(!buf) {out("ERROR=NO_MEMORY\n");goto end;}
    got=DdeGetData(data,buf,bytes,0);
    if(got!=bytes) {out("ERROR=DdeGetData copied=%lu expected=%lu\n",(unsigned long)got,(unsigned long)bytes);goto end;}
    dump_hex(buf,bytes);
    decode_frame(buf,bytes,fmt);
    rc=0;
end:
    if(buf) free(buf);
    if(data) DdeFreeDataHandle(data);
    if(conv) DdeDisconnect(conv);
    if(g_instance) {
        if(h_item) DdeFreeStringHandle(g_instance,h_item);
        if(h_topic) DdeFreeStringHandle(g_instance,h_topic);
        if(h_service) DdeFreeStringHandle(g_instance,h_service);
        DdeUninitialize(g_instance);
    }
    out("EXIT=%d\n",rc);
    if(g_log) fclose(g_log);
    return rc;
}
