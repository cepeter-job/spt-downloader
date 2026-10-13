"""Temporary test-only visual evidence. Synthetic GUI, no worker/account/portal."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import date
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import time
import tkinter as tk
import zlib

from spt_desktop.app import App


class Rect(ctypes.Structure):
    _fields_ = [('left',wintypes.LONG),('top',wintypes.LONG),('right',wintypes.LONG),('bottom',wintypes.LONG)]


class BitmapHeader(ctypes.Structure):
    _fields_ = [('size',wintypes.DWORD),('width',wintypes.LONG),('height',wintypes.LONG),
                ('planes',wintypes.WORD),('bit_count',wintypes.WORD),('compression',wintypes.DWORD),
                ('size_image',wintypes.DWORD),('x_pels_per_meter',wintypes.LONG),
                ('y_pels_per_meter',wintypes.LONG),('clr_used',wintypes.DWORD),('clr_important',wintypes.DWORD)]


class BitmapInfo(ctypes.Structure):
    _fields_ = [('header',BitmapHeader),('colors',wintypes.DWORD*1)]


class FakeController:
    def __init__(self):
        self.active = False
        self.operation = 'export'
        self.job_id = None
        self.starts = 0

    def start(self,*args):
        if self.active:
            raise AssertionError('Duplicate synthetic start')
        self.starts += 1
        self.job_id = 'synthetic-job-01'
        self.active = True
        return self.job_id

    def poll(self):
        return self.active

    def stop(self):
        self.active = False

    def close(self):
        self.active = False


user32=ctypes.WinDLL('user32',use_last_error=True)
gdi32=ctypes.WinDLL('gdi32',use_last_error=True)
user32.GetAncestor.argtypes=(wintypes.HWND,wintypes.UINT)
user32.GetAncestor.restype=wintypes.HWND
user32.GetWindowRect.argtypes=(wintypes.HWND,ctypes.POINTER(Rect))
user32.GetWindowRect.restype=wintypes.BOOL
user32.GetWindowDC.argtypes=(wintypes.HWND,)
user32.GetWindowDC.restype=wintypes.HDC
user32.ReleaseDC.argtypes=(wintypes.HWND,wintypes.HDC)
user32.ReleaseDC.restype=ctypes.c_int
user32.GetDC.argtypes=(wintypes.HWND,)
user32.GetDC.restype=wintypes.HDC
user32.PrintWindow.argtypes=(wintypes.HWND,wintypes.HDC,wintypes.UINT)
user32.PrintWindow.restype=wintypes.BOOL
gdi32.CreateCompatibleDC.argtypes=(wintypes.HDC,)
gdi32.CreateCompatibleDC.restype=wintypes.HDC
gdi32.CreateCompatibleBitmap.argtypes=(wintypes.HDC,ctypes.c_int,ctypes.c_int)
gdi32.CreateCompatibleBitmap.restype=wintypes.HBITMAP
gdi32.SelectObject.argtypes=(wintypes.HDC,wintypes.HGDIOBJ)
gdi32.SelectObject.restype=wintypes.HGDIOBJ
gdi32.DeleteObject.argtypes=(wintypes.HGDIOBJ,)
gdi32.DeleteObject.restype=wintypes.BOOL
gdi32.DeleteDC.argtypes=(wintypes.HDC,)
gdi32.DeleteDC.restype=wintypes.BOOL
gdi32.GetDIBits.argtypes=(wintypes.HDC,wintypes.HBITMAP,wintypes.UINT,wintypes.UINT,ctypes.c_void_p,ctypes.POINTER(BitmapInfo),wintypes.UINT)
gdi32.GetDIBits.restype=ctypes.c_int
gdi32.BitBlt.argtypes=(wintypes.HDC,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,wintypes.HDC,ctypes.c_int,ctypes.c_int,wintypes.DWORD)
gdi32.BitBlt.restype=wintypes.BOOL


def chunk(typ:bytes, data:bytes)->bytes:
    return struct.pack('>I',len(data))+typ+data+struct.pack('>I',zlib.crc32(typ+data)&0xffffffff)


def png_from_bgra(raw:bytes,width:int,height:int)->bytes:
    rgba=bytearray(len(raw))
    for i in range(0,len(raw),4):
        rgba[i:i+4]=bytes((raw[i+2],raw[i+1],raw[i],255))
    stride=width*4
    rows=b''.join(b'\x00'+rgba[y*stride:(y+1)*stride] for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>2I5B',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows,6))+chunk(b'IEND',b'')


def grab(hwnd:int, mode:str):
    rect=Rect()
    assert user32.GetWindowRect(hwnd,ctypes.byref(rect)),ctypes.get_last_error()
    width,height=rect.right-rect.left,rect.bottom-rect.top
    assert 250<=width<=2500 and 250<=height<=2000,(width,height)
    src=user32.GetWindowDC(hwnd) if mode=='printwindow' else user32.GetDC(0)
    assert src
    dc=gdi32.CreateCompatibleDC(src)
    bitmap=gdi32.CreateCompatibleBitmap(src,width,height)
    assert dc and bitmap
    original=gdi32.SelectObject(dc,bitmap)
    try:
        if mode=='printwindow':
            ok=bool(user32.PrintWindow(hwnd,dc,2))
        else:
            ok=bool(gdi32.BitBlt(dc,0,0,width,height,src,rect.left,rect.top,0x00CC0020|0x40000000))
        info=BitmapInfo()
        info.header.size=ctypes.sizeof(BitmapHeader)
        info.header.width=width
        info.header.height=-height
        info.header.planes=1
        info.header.bit_count=32
        info.header.compression=0
        buffer=ctypes.create_string_buffer(width*height*4)
        count=gdi32.GetDIBits(dc,bitmap,0,height,buffer,ctypes.byref(info),0)
        assert count==height,('GetDIBits',count,height,ctypes.get_last_error())
        raw=buffer.raw
        colors={tuple(raw[i:i+3]) for i in range(0,len(raw),max(4,len(raw)//7000//4*4))}
        return png_from_bgra(raw,width,height),{'ok':ok,'width':width,'height':height,'color_sample_count':len(colors),
                    'first_pixel_bgra':list(raw[:4]),'rect':[rect.left,rect.top,rect.right,rect.bottom]}
    finally:
        gdi32.SelectObject(dc,original)
        gdi32.DeleteObject(bitmap)
        gdi32.DeleteDC(dc)
        if mode=='printwindow': user32.ReleaseDC(hwnd,src)
        else: user32.ReleaseDC(0,src)


def tick(root):
    for _ in range(4):
        root.update_idletasks();root.update();time.sleep(0.12)


def bounds(widget):
    return {'x':widget.winfo_rootx(),'y':widget.winfo_rooty(),
            'width':widget.winfo_width(),'height':widget.winfo_height(),
            'mapped':bool(widget.winfo_ismapped())}


def snapshot(out, key, width, height, state):
    root=tk.Tk()
    root.withdraw()
    controller=FakeController()
    try:
        with tempfile.TemporaryDirectory(prefix='t5-ui-synthetic-') as td:
            app=App(root,td,controller=controller)
            root.geometry(f'{width}x{height}+28+28')
            root.deiconify()
            root.lift()
            tick(root)
            if state=='invalid':
                app.npwp.set('bad-npwp');app.year.set('20');app.start()
                assert not controller.active
            elif state!='idle':
                app.npwp.set('0000000000000001');app.year.set('2025');app.start()
                assert controller.active and controller.starts==1
                if state=='details':
                    app.on_event({'job_id':controller.job_id,'type':'progress','stage':'details',
                        'percent':66,'processed':6,'total':9,'verified':5,'message':'Membaca SPT pilihan…'})
                elif state=='complete':
                    controller.active=False
                    output=Path(td)/'synthetic-output';output.mkdir()
                    app.on_event({'job_id':controller.job_id,'type':'terminal','status':'COMPLETE',
                         'percent':100,'output':str(output),'message':'SPT yang dipilih selesai diperiksa.'})
                elif state=='partial':
                    controller.active=False
                    output=Path(td)/'synthetic-output';output.mkdir()
                    app.on_event({'job_id':controller.job_id,'type':'terminal','status':'PARTIAL',
                         'percent':90,'output':str(output),'message':'Beberapa rincian belum lengkap.'})
                else: raise AssertionError(state)
            tick(root)
            hwnd=user32.GetAncestor(root.winfo_id(),2)
            images={}
            for mode in ('printwindow','bitblt'):
                image,meta=grab(hwnd,mode)
                name=f'{key}-{mode}.png'
                (out/name).write_bytes(image)
                images[mode]={**meta,'sha256':hashlib.sha256(image).hexdigest(),'filename':name}
            rects={name:bounds(widget) for name,widget in [('heading',app.view.heading),('settings',app.settings_button),
                 ('stages',app.view.stage_strip),('summary',app.view.scope_panel),('form',app.view.form),
                 ('process',app.view.progress_panel),('result',app.view.result_panel),
                 ('actions',app.view.action_bar),('footer',app.view.results_label),('scroll',app.view.canvas)]}
            if width<960: assert rects['summary']['y'] < rects['form' if state in ('idle','invalid') else 'process']['y']
            else: assert rects['summary']['x'] > rects['form' if state in ('idle','invalid') else 'process']['x']
            assert app.view.heading.cget('text')=='Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang'
            assert app.results_label.cget('text')=='Hasil Sedot berada di folder Downloads Windows'
            assert app.view.footer.winfo_ismapped()
            assert all(x['width']>0 and x['height']>0 for x in rects.values())
            def scroll_state():
                return {'yview':list(app.view.canvas.yview()),
                        'scrollregion':str(app.view.canvas.cget('scrollregion')),
                        'workspace_height':app.view.workspace.winfo_height(),
                        'entry':bounds(app.npwp_entry),
                        'caption':bounds(next(child for child in app.view.npwp_field.winfo_children()
                                              if child.winfo_class()=='TLabel' and child.cget('text')=='NPWP (16 digit)')),
                        'scope_title':bounds(app.view.scope_title),
                        'form_title':bounds(app.view.form_title),
                        'year_entry':bounds(app.year_entry),
                        'result':bounds(app.view.result_title_label),
                        'pending':app.view._pending_reveal,
                        'reveal_callback':app.view._reveal_after}
            before=scroll_state()
            # Diagnostic only, after all evidence screenshots. Does the same
            # reveal algorithm scroll once the geometry has fully settled?
            app.view._pending_reveal=app.view._priority_area(app.view._state)
            app.view._reveal_priority()
            tick(root)
            after=scroll_state()
            report={'key':key,'state':state,'request':[width,height],
                    'client':[root.winfo_width(),root.winfo_height()],
                    'screen':[root.winfo_screenwidth(),root.winfo_screenheight()],
                    'rects':rects,'status':app.status.get(),'images':images,
                    'scroll_diagnostic':{'before':before,'after_manual_reveal':after}}
            print('SCROLL',key,before['yview'],after['yview'],before['workspace_height'],flush=True)
            app._dispose();controller.close()
            return report
    finally:
        try: root.destroy()
        except tk.TclError:pass


def try_larger_virtual_desktop():
    """Only alter this disposable hosted Windows runner, never the product DPI mode."""
    class DevMode(ctypes.Structure):
        _fields_ = [('device', wintypes.WCHAR*32),('spec',wintypes.WORD),
            ('driver',wintypes.WORD),('size',wintypes.WORD),('extra',wintypes.WORD),
            ('fields',wintypes.DWORD),('x',wintypes.LONG),('y',wintypes.LONG),
            ('orientation',wintypes.DWORD),('fixed',wintypes.DWORD),
            ('color',wintypes.SHORT),('duplex',wintypes.SHORT),
            ('yresolution',wintypes.SHORT),('tt',wintypes.SHORT),('collate',wintypes.SHORT),
            ('form',wintypes.WCHAR*32),('log_pixels',wintypes.WORD),
            ('bits_per_pixel',wintypes.DWORD),('pixels_width',wintypes.DWORD),
            ('pixels_height',wintypes.DWORD),('display_flags',wintypes.DWORD),
            ('display_frequency',wintypes.DWORD),('icm_method',wintypes.DWORD),
            ('icm_intent',wintypes.DWORD),('media_type',wintypes.DWORD),
            ('dither_type',wintypes.DWORD),('reserved1',wintypes.DWORD),
            ('reserved2',wintypes.DWORD),('panning_width',wintypes.DWORD),
            ('panning_height',wintypes.DWORD)]
    expected=220
    if ctypes.sizeof(DevMode)!=expected:
        print('SKIP_RESOLUTION_CHANGE_BAD_STRUCT',ctypes.sizeof(DevMode),flush=True)
        return 'not attempted: devmode layout mismatch'
    user32.EnumDisplaySettingsW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(DevMode))
    user32.EnumDisplaySettingsW.restype=wintypes.BOOL
    user32.ChangeDisplaySettingsW.argtypes=(ctypes.POINTER(DevMode),wintypes.DWORD)
    user32.ChangeDisplaySettingsW.restype=wintypes.LONG
    modes=[]
    for idx in range(512):
        mode=DevMode();mode.size=ctypes.sizeof(DevMode)
        if not user32.EnumDisplaySettingsW(None,idx,ctypes.byref(mode)):
            break
        if mode.bits_per_pixel>=24:
            modes.append((int(mode.pixels_width),int(mode.pixels_height),idx))
    candidates=sorted((m for m in modes if m[0]>=1280 and m[1]>=900),
                      key=lambda x:(x[0]*x[1],x[0]))
    print('AVAILABLE_DISPLAY_MODES',len(modes), 'larger',candidates[:10],flush=True)
    for width,height,idx in candidates:
        mode=DevMode();mode.size=ctypes.sizeof(DevMode)
        if not user32.EnumDisplaySettingsW(None,idx,ctypes.byref(mode)):
            continue
        mode.fields=0x00080000|0x00100000
        if user32.ChangeDisplaySettingsW(ctypes.byref(mode),2)!=0:
            continue
        status=user32.ChangeDisplaySettingsW(ctypes.byref(mode),0)
        if status==0:
            time.sleep(1)
            print('DISPLAY_RESOLUTION_CHANGED',width,height,flush=True)
            return f'{width}x{height}'
    print('NO_LARGER_DISPLAY_MODE_AVAILABLE',flush=True)
    return 'larger mode unavailable'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    display_result=try_larger_virtual_desktop()
    states=[('regular-idle',1120,800,'idle'),('compact-idle',640,560,'idle'),
            ('compact-invalid',640,560,'invalid'),('regular-details',1120,800,'details'),
            ('compact-details',640,560,'details'),('regular-complete',1120,800,'complete'),
            ('compact-partial',640,560,'partial'),('tiny-idle',540,390,'idle')]
    reports=[]
    for key,width,height,state in states:
        data=snapshot(args.out,key,width,height,state)
        reports.append(data)
        print('FRAME',key,data['client'],data['screen'],{m:e['color_sample_count'] for m,e in data['images'].items()},flush=True)
    assert all(any(im['ok'] and im['color_sample_count']>24 for im in entry['images'].values()) for entry in reports)
    (args.out/'manifest.json').write_text(json.dumps({'synthetic':True,'no_portal':True,'display_setup':display_result,'frames':reports},ensure_ascii=False,indent=2),encoding='utf-8')
    print('T5_SYNTHETIC_CAPTURE_OK',len(reports),flush=True)

if __name__=='__main__':
    main()
