"use strict";
// Accessible precise seeking. Native controls remain a fallback until enhancement.
(() => {
  function timeText(seconds, tenths=false) {
    if (!Number.isFinite(seconds)) return "--:--";
    const v=Math.max(0,seconds),m=Math.floor(v/60),s=Math.floor(v%60);
    return String(m).padStart(2,"0")+":"+String(s).padStart(2,"0")+(tenths?"."+Math.floor((v%1)*10):"");
  }
  function parseTime(text) {
    const raw=String(text).trim().replace(",",".");
    if (/^\d+(?:\.\d+)?$/.test(raw)) return Number(raw);
    const m=raw.match(/^(\d+):(\d{1,2}(?:\.\d+)?)$/);
    return m && Number(m[2])<60 ? Number(m[1])*60+Number(m[2]) : NaN;
  }
  let serial=0;
  function enhance(audio) {
    if (audio.id==="studio34Audio") return; // Shared transport has its own controls.
    if (audio.dataset.precisePlayer) return;
    audio.dataset.precisePlayer="1";audio.preload="metadata";
    const id="music-player-"+(++serial),wrap=document.createElement("div");
    wrap.className="precise-player";wrap.dataset.forAudio=audio.id || id;
    wrap.innerHTML='<div class="player-actions"><button type="button" class="player-play" aria-label="Воспроизвести">▶</button><button type="button" class="player-back" aria-label="Назад на пять секунд">−5 с</button><button type="button" class="player-forward" aria-label="Вперёд на пять секунд">+5 с</button><output class="player-clock">00:00 / --:--</output></div><label class="player-seek-label"><span class="sr-only">Позиция воспроизведения в секундах</span><input class="player-seek" type="range" min="0" max="1" step="0.1" value="0" disabled></label><div class="player-exact"><label>Перейти к <input class="player-time" type="text" inputmode="decimal" placeholder="01:23.5" aria-label="Время: минуты:секунды или число секунд"></label><button class="player-go" type="button">Перейти</button><label class="player-volume-label">Громкость <input class="player-volume" type="range" min="0" max="1" step="0.01" value="1" aria-label="Громкость плеера"></label></div><span class="player-hint" role="status"></span>';
    audio.insertAdjacentElement("afterend",wrap);
    const q=s=>wrap.querySelector(s),seek=q('.player-seek'),clock=q('.player-clock'),play=q('.player-play'),input=q('.player-time'),hint=q('.player-hint');
    let dragging=false,pending=null;
    const duration=()=>Number.isFinite(audio.duration)&&audio.duration>0?audio.duration:0;
    function seekTo(t) {
      if (!Number.isFinite(t)) {hint.textContent="Укажи секунды или время, например 01:23.5.";return;}
      if (!duration()) {pending=Math.max(0,t);audio.load();hint.textContent="Загружаем длительность…";return;}
      audio.currentTime=Math.min(duration(),Math.max(0,t));hint.textContent="";render();
    }
    function render() {
      const d=duration();seek.disabled=!d;seek.max=String(d||1);
      if (!dragging) seek.value=String(audio.currentTime||0);
      const position=dragging?Number(seek.value):audio.currentTime||0;
      clock.textContent=timeText(position,true)+" / "+timeText(d||NaN);
      seek.setAttribute('aria-valuetext',timeText(position,true)+' из '+timeText(d||NaN));
      play.textContent=audio.paused?'▶':'Ⅱ';play.setAttribute('aria-label',audio.paused?'Воспроизвести':'Пауза');
      if(d)seek.style.setProperty('--progress',(100*position/d)+'%');
    }
    play.addEventListener('click',async()=>{try{if(audio.paused)await audio.play();else audio.pause();}catch(e){hint.textContent="Не удалось включить звук: "+e.message;}});
    q('.player-back').addEventListener('click',()=>seekTo(audio.currentTime-5));
    q('.player-forward').addEventListener('click',()=>seekTo(audio.currentTime+5));
    seek.addEventListener('pointerdown',()=>{dragging=true;});
    seek.addEventListener('input',()=>{dragging=true;render();});
    const commit=()=>{if(dragging){const value=Number(seek.value);dragging=false;seekTo(value);}};
    seek.addEventListener('change',commit);seek.addEventListener('pointerup',commit);seek.addEventListener('pointercancel',()=>{dragging=false;render();});
    seek.addEventListener('blur',commit);
    seek.addEventListener('keydown',e=>{
      if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();dragging=false;seekTo(audio.currentTime+(e.key==='ArrowRight'?1:-1)*(e.shiftKey?5:1));}
      else if(e.key==='Home'){e.preventDefault();seekTo(0);}else if(e.key==='End'){e.preventDefault();seekTo(duration());}
    });
    const jump=()=>seekTo(parseTime(input.value));q('.player-go').addEventListener('click',jump);
    input.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();jump();}});
    q('.player-volume').addEventListener('input',e=>{audio.volume=Number(e.target.value);audio.muted=false;});
    audio.addEventListener('loadedmetadata',()=>{render();if(pending!==null){const p=pending;pending=null;seekTo(p);}});
    ['timeupdate','durationchange','pause','ended','seeked','loadeddata'].forEach(event=>audio.addEventListener(event,render));
    audio.addEventListener('play',()=>{document.querySelectorAll('audio').forEach(other=>{if(other!==audio&&!other.paused)other.pause();});render();});
    audio.addEventListener('error',()=>{hint.textContent="Аудио не загрузилось. Проверь, существует ли файл.";});
    // Preserve the recorder's hidden preview state without observing all controls.
    const hiddenState=()=>{wrap.hidden=audio.classList.contains('hidden')||audio.hidden;};
    new MutationObserver(hiddenState).observe(audio,{attributes:true,attributeFilter:['class','hidden','src']});
    audio.controls=false;audio.style.display='none';hiddenState();render();
  }
  function scan(node) {if(node.nodeType!==1)return;if(node.matches('audio'))enhance(node);node.querySelectorAll('audio').forEach(enhance);}
  document.querySelectorAll('audio').forEach(enhance);
  new MutationObserver(records=>records.forEach(r=>r.addedNodes.forEach(scan))).observe(document.body,{childList:true,subtree:true});
  window.musicPlayerTime={parse:parseTime,format:timeText};
})();
