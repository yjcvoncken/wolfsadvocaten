"""Capture rendered geometry and scroll states for visual comparison."""
import argparse,json,time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

parser=argparse.ArgumentParser();parser.add_argument('--url',default='https://www.wolfsadvocaten.nl/');parser.add_argument('--width',type=int,default=1440);parser.add_argument('--height',type=int,default=900);parser.add_argument('--output',default='/tmp/wolfs-reference');args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
o=Options();o.add_argument('--headless=new');o.add_argument('--no-sandbox');o.add_argument(f'--window-size={args.width},{args.height}');o.page_load_strategy='eager'
d=webdriver.Chrome(options=o)
try:
 d.get(args.url);time.sleep(8)
 d.execute_script("document.documentElement.style.scrollBehavior='auto'")
 height=d.execute_script('return document.documentElement.scrollHeight')
 for y in range(0,height,600):
  d.execute_script('window.scrollTo(0,arguments[0])',y);time.sleep(.16)
 d.execute_script('window.scrollTo(0,0)');time.sleep(2)
 report=d.execute_script('''
 const properties=['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','color','backgroundColor','position','top','borderRadius','display','gridTemplateColumns','gap','padding','margin','opacity','transform'];
 function data(e){const r=e.getBoundingClientRect(),s=getComputedStyle(e);return {id:e.id,tag:e.tagName,classes:e.className?.baseVal??e.className,text:(e.innerText||e.alt||'').trim(),src:e.currentSrc||e.src,href:e.href,x:r.x,y:r.y+scrollY,w:r.width,h:r.height,style:Object.fromEntries(properties.map(p=>[p,s[p]]))}}
 const visible=e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0};
 return {width:innerWidth,height:innerHeight,scrollHeight:document.documentElement.scrollHeight,sections:[...document.querySelectorAll('main section')].filter(visible).map(data),elements:[...document.querySelectorAll('h1,h2,h3,p,main img,header a,footer a')].filter(visible).map(data),sticky:[...document.querySelectorAll('main *')].filter(e=>getComputedStyle(e).position==='sticky'&&visible(e)).map(data)};
 ''')
 (out/'geometry.json').write_text(json.dumps(report,indent=2))
 for y in [0,600,1200,1800,2400,3000,4000,5000,6000,7000,8000,9000]:
  if y>=height:break
  d.execute_script('window.scrollTo(0,arguments[0])',y);time.sleep(.75);d.save_screenshot(str(out/f'scroll-{y}.png'))
 print(json.dumps({'output':str(out),'width':report['width'],'height':report['height'],'scrollHeight':report['scrollHeight'],'sections':len(report['sections']),'elements':len(report['elements']),'sticky':len(report['sticky'])}),flush=True)
finally:d.quit()
