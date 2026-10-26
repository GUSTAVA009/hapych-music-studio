"use strict";
/* Music Studio 3.6 micro interactions, inspired by Vue Bits.
   Uses native DOM; no external packages, no synthetic progress and no network CDN.
*/
(() => {
  const $ = id => document.getElementById(id);
  const make = (tag, cls, text) => {
    const n=document.createElement(tag);
    if(cls)n.className=cls;
    if(text!==undefined)n.textContent=text;
    return n;
  };
  const motionOff=matchMedia("(prefers-reduced-motion: reduce)");
  const request=(url, payload) => window.call
    ? window.call(url, {method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})
    : fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)})
      .then(async res=>{const j=await res.json();if(!res.ok)throw Error(j.error||"Не удалось выполнить действие");return j;});
  const phaseName={
    preparing:"Подготавливаем композицию", generating:"Создаём музыку",
    converting:"Обрабатываем вокал и сводим", done:"Генерация завершена",
    error:"Ошибка создания трека"
  };

  // Thought Line — reflects server-reported phases/messages only.
  const feed=document.querySelector("#page-create .studio34-feed");
  const header=feed?.querySelector(".studio34-feed-title");
  const thought=make("section","micro36-thought");
  thought.id="micro36Thought";
  thought.hidden=true;
  thought.setAttribute("aria-label","Ход генерации");
  const head=make("button","micro36-thought-head");
  head.type="button";head.setAttribute("aria-expanded","true");head.setAttribute("aria-controls","micro36ThoughtTrace");
  head.innerHTML='<span class="micro36-thought-glyph" aria-hidden="true">✦</span><span class="micro36-thought-current">Ожидаем задачу</span><time class="micro36-thought-clock" aria-label="Прошедшее время">0:00</time><span class="micro36-thought-chevron" aria-hidden="true">⌄</span>';
  const trace=make("ol","micro36-thought-trace");
  trace.id="micro36ThoughtTrace";
  thought.append(head,trace);
  if(header)header.insertAdjacentElement("afterend",thought);
  head.addEventListener("click",()=>{
    const expanded=head.getAttribute("aria-expanded")!=="true";
    head.setAttribute("aria-expanded",String(expanded));
    trace.hidden=!expanded;
  });
  const thoughtText=head.querySelector(".micro36-thought-current");
  const clock=head.querySelector(".micro36-thought-clock");
  let currentJobId=null,jobStarted=0,jobFinished=false,lastPhase="",lastMsg="";
  let traceItems=[];
  const formatTime=seconds=>{
    const n=Math.max(0,Math.floor(seconds));
    return Math.floor(n/60)+":"+String(n%60).padStart(2,"0");
  };
  const tick=()=>{
    if(thought.hidden||!jobStarted)return;
    clock.textContent=formatTime((Date.now()-jobStarted)/1000);
  };
  let settleTimeout=null;
  setInterval(tick,1000);
  function paintTrace(){
    trace.replaceChildren(...traceItems.slice(-7).map((line,i,arr)=>{
      const el=make("li","micro36-trace-item"+(i===arr.length-1&&!jobFinished?" active":""),line);
      return el;
    }));
  }
  function jobUpdate(job){
    if(!job||typeof job.status!=="string")return;
    const busy=["preparing","generating","converting"].includes(job.status);
    const id=job.id||null;
    if(busy && ((id&&id!==currentJobId)||(!currentJobId&&jobFinished)||(!jobStarted))){
      currentJobId=id;jobFinished=false;lastPhase="";lastMsg="";traceItems=[];
      head.setAttribute("aria-expanded","true");
      trace.hidden=false;
      const started=job.started?Date.parse(job.started):NaN;
      jobStarted=Number.isFinite(started)?started:Date.now();
    }
    if(busy){
      clearTimeout(settleTimeout);
      thought.hidden=false;thought.classList.add("is-working");thought.classList.remove("is-done","is-error");
      const name=phaseName[job.status]||"Выполняется генерация";
      const message=String(job.message||"").trim();
      if(job.status!==lastPhase){traceItems.push(name);lastPhase=job.status;}
      if(message && message!==lastMsg && message!==name){
        traceItems.push(message);lastMsg=message;
      }
      thoughtText.textContent=message||name;
      jobFinished=false;paintTrace();tick();
      return;
    }
    if(!jobStarted && job.status!=="error")return;
    if(["done","error"].includes(job.status)){
      if(!jobFinished){
        jobFinished=true;lastPhase=job.status;
        thought.classList.remove("is-working");thought.classList.add(job.status==="error"?"is-error":"is-done");
        thought.hidden=false;
        const msg=job.status==="error"?(job.error||job.message||"Ошибка генерации"):
          (job.message||phaseName.done);
        thoughtText.textContent=String(msg).slice(0,240);
        traceItems.push(job.status==="error"?"Ошибка обработки":"Готово, результат сохранён");
        paintTrace();tick();
        // Settle to a single line, preserving the trace behind a disclosure.
        head.setAttribute("aria-expanded","false");
        trace.hidden=true;
        clearTimeout(settleTimeout);
        settleTimeout=setTimeout(()=>{if(!thought.classList.contains("is-working"))thought.hidden=true;},12000);
      }
    }else if(!jobFinished){
      thought.hidden=true;
    }
  }
  window.studio36OnJob=jobUpdate;

  // Swipe Row: a horizontal drag reveals two safe, labeled actions.
  let activeSwipe=null;
  function closeOtherRows(exception){
    document.querySelectorAll(".micro36-swipe-host.open").forEach(row=>{
      if(row!==exception){row.classList.remove("open");row.style.setProperty("--micro36-shift","0px");}
    });
  }
  function enhanceRow(row){
    if(row.dataset.micro36Ready)return;
    row.dataset.micro36Ready="1";
    row.classList.add("micro36-swipe-host");
    const face=make("div","micro36-swipe-face");
    while(row.firstChild)face.append(row.firstChild);
    const actions=make("div","micro36-swipe-actions");
    const remove=make("button","micro36-swipe-remove","▤ В корзину");
    remove.type="button";remove.setAttribute("aria-label","Переместить трек в корзину и дать возможность отменить");
    remove.addEventListener("click",e=>{
      e.preventDefault();e.stopPropagation();
      window.studio36DeleteTrack?.({
        name:row.dataset.filename,
        title:face.querySelector("strong")?.textContent||row.dataset.filename
      });
    });
    actions.append(remove);
    row.append(actions,face);
    row.addEventListener("pointerdown",e=>{
      if(e.button!==0||e.target.closest("button,a,input,textarea,select"))return;
      activeSwipe={id:e.pointerId,row,startX:e.clientX,startY:e.clientY,base:row.classList.contains("open")?-112:0,dragging:false};
    });
    row.addEventListener("pointermove",e=>{
      const s=activeSwipe;
      if(!s||s.id!==e.pointerId||s.row!==row)return;
      const dx=e.clientX-s.startX,dy=e.clientY-s.startY;
      if(!s.dragging){
        if(Math.abs(dx)<10)return;
        if(Math.abs(dy)>Math.abs(dx)*.95){activeSwipe=null;return;}
        s.dragging=true;
        row.setPointerCapture?.(e.pointerId);
        row.classList.add("dragging");
        closeOtherRows(row);
      }
      const next=Math.max(-112,Math.min(0,s.base+dx));
      row.style.setProperty("--micro36-shift",next+"px");
      if(e.cancelable)e.preventDefault();
    },{passive:false});
    function finish(e){
      const s=activeSwipe;
      if(!s||s.id!==e.pointerId||s.row!==row)return;
      activeSwipe=null;
      row.classList.remove("dragging");
      if(!s.dragging)return;
      const delta=e.clientX-s.startX;
      const opened=s.base+delta< -47;
      row.classList.toggle("open",opened);
      row.style.setProperty("--micro36-shift",opened?"-112px":"0px");
      row.dataset.micro36Suppress="1";
      setTimeout(()=>{delete row.dataset.micro36Suppress;},400);
    }
    row.addEventListener("pointerup",finish);
    row.addEventListener("pointercancel",()=>{
      activeSwipe=null;row.classList.remove("dragging");
      row.style.setProperty("--micro36-shift",row.classList.contains("open")?"-112px":"0px");
    });
    row.addEventListener("click",e=>{
      if(row.dataset.micro36Suppress==="1"){
        e.preventDefault();e.stopImmediatePropagation();
        delete row.dataset.micro36Suppress;
      }
    },true);
    row.addEventListener("keydown",e=>{
      if(e.target!==row)return;
      if(e.key==="ArrowLeft"){e.preventDefault();closeOtherRows(row);row.classList.add("open");row.style.setProperty("--micro36-shift","-112px");remove.focus();}
      if(e.key==="ArrowRight"&&row.classList.contains("open")){
        e.preventDefault();row.classList.remove("open");row.style.setProperty("--micro36-shift","0px");
      }
    });
  }
  function enhanceTrackRows(){
    document.querySelectorAll("#studio34FeedList .studio34-track-row,#tracksList .studio34-track-row").forEach(enhanceRow);
  }
  for(const id of ["studio34FeedList","tracksList"]){
    const list=$(id);
    if(list)new MutationObserver(enhanceTrackRows).observe(list,{childList:true});
  }
  enhanceTrackRows();

  // Swipe Toast: provide a genuine, server-backed undo.
  const toast=make("div","micro36-undo-toast");
  toast.id="micro36UndoToast";toast.hidden=true;
  toast.setAttribute("role","status");toast.setAttribute("aria-live","polite");
  const toastIcon=make("span","micro36-undo-icon","↶");
  const toastBody=make("div","micro36-undo-body");
  const toastTitle=make("strong","","Перемещено в корзину");
  const toastCaption=make("small","","Можно восстановить");
  toastBody.append(toastTitle,toastCaption);
  const toastUndo=make("button","micro36-undo-action","Вернуть");
  toastUndo.type="button";
  const toastClose=make("button","micro36-undo-close","×");
  toastClose.type="button";toastClose.setAttribute("aria-label","Закрыть уведомление");
  const fuse=make("div","micro36-undo-fuse");
  toast.append(toastIcon,toastBody,toastUndo,toastClose,fuse);
  document.body.append(toast);
  let toastToken="",toastTarget="",toastTimeout=null,toastGesture=null;
  function dismissToast(){
    toast.hidden=true;toast.classList.remove("enter","dragging");
    toastToken="";toastTarget="";
    clearTimeout(toastTimeout);
    toast.style.removeProperty("--micro36-toast-y");
  }
  function showUndo(file,token){
    toastToken=token||"";toastTarget=file.name;
    toastTitle.textContent="Трек перемещён в корзину";
    toastCaption.textContent=String(file.title||file.name).slice(0,68);
    toastUndo.hidden=!token;toastUndo.disabled=false;toastUndo.textContent="Вернуть";
    toast.classList.remove("enter");toast.hidden=false;
    void toast.offsetWidth;toast.classList.add("enter");
    clearTimeout(toastTimeout);
    toastTimeout=setTimeout(dismissToast,11000);
  }
  toastClose.addEventListener("click",dismissToast);
  toastUndo.addEventListener("click",async()=>{
    if(!toastToken||!toastTarget)return;
    toastUndo.disabled=true;toastUndo.textContent="Возвращаем…";
    try{
      await request("/api/restore_track",{token:toastToken,name:toastTarget});
      dismissToast();
      await window.refreshTracks?.();
      if(typeof window.notify==="function")window.notify("Трек восстановлен в библиотеке.");
    }catch(e){
      toastUndo.disabled=false;toastUndo.textContent="Повторить";
      toastCaption.textContent=String(e.message||e).slice(0,120);
      clearTimeout(toastTimeout);
      toastTimeout=setTimeout(dismissToast,12000);
    }
  });
  toast.addEventListener("pointerdown",e=>{if(e.target.closest("button"))return;toastGesture={id:e.pointerId,start:e.clientY};});
  toast.addEventListener("pointermove",e=>{
    if(!toastGesture||toastGesture.id!==e.pointerId)return;
    const y=Math.max(0,e.clientY-toastGesture.start);
    toast.classList.add("dragging");toast.style.setProperty("--micro36-toast-y",Math.min(y,120)+"px");
  });
  toast.addEventListener("pointerup",e=>{
    if(!toastGesture||toastGesture.id!==e.pointerId)return;
    const dy=e.clientY-toastGesture.start;
    toastGesture=null;toast.classList.remove("dragging");
    if(dy>45)dismissToast();
    else toast.style.removeProperty("--micro36-toast-y");
  });
  toast.addEventListener("pointercancel",()=>{toastGesture=null;toast.classList.remove("dragging");toast.style.removeProperty("--micro36-toast-y")});

  let removing=new Set();
  window.studio36DeleteTrack=async file=>{
    const filename=String(file?.name||"");
    if(!filename||removing.has(filename))return false;
    removing.add(filename);
    try{
      const result=await request("/api/remove_track",{name:filename});
      if(window.studio36OnRemoved)window.studio36OnRemoved(filename);
      closeOtherRows();
      await window.refreshTracks?.();
      showUndo(file,result.undo_token);
      return true;
    }catch(e){
      if(typeof window.notify==="function")window.notify(e.message||"Не удалось переместить трек",true);
      return false;
    }finally{removing.delete(filename);}
  };

  // Prompt Bar: enhance existing inputs, keep ids, values and backend events.
  async function copy(text){
    if(!text){window.notify?.("Поле пока пустое.");return;}
    try{await navigator.clipboard.writeText(text);window.notify?.("Текст скопирован.");}
    catch(e){window.notify?.("Не удалось скопировать текст.",true);}
  }
  function wrapInput(id,label,actionId){
    const editor=$(id);
    if(!editor||editor.closest(".micro36-prompt-bar"))return;
    const parent=editor.parentNode;
    const shell=make("div","micro36-prompt-bar");
    shell.dataset.input=id;
    parent.insertBefore(shell,editor);
    shell.append(editor);
    const foot=make("div","micro36-prompt-foot");
    const info=make("span","micro36-prompt-info");
    const actions=make("div","micro36-prompt-actions");
    const copyButton=make("button","micro36-copy-control","⧉");
    copyButton.type="button";copyButton.title="Копировать содержимое";copyButton.setAttribute("aria-label","Копировать "+label);
    copyButton.addEventListener("click",()=>copy(editor.value));
    const submit=make("button","micro36-prompt-send","↗");
    submit.type="button";submit.title="Выполнить действие • Ctrl+Enter";
    submit.setAttribute("aria-label",id==="style"?"Проверить описание стиля":id==="lyrics"?"Создать песню":"Сгенерировать текст");
    submit.addEventListener("click",()=>$(actionId)?.click());
    actions.append(copyButton,submit);
    foot.append(info,actions);shell.append(foot);
    const counter=()=>{
      info.textContent=(id==="style"?"Стиль · ":"Текст · ")+editor.value.length.toLocaleString("ru-RU")+" зн. · Ctrl+Enter";
      submit.disabled=editor.disabled||!editor.value.trim();
    };
    editor.addEventListener("input",counter);
    editor.addEventListener("change",counter);
    editor.addEventListener("keydown",e=>{
      if(e.key==="Enter"&&(e.ctrlKey||e.metaKey)&&!editor.disabled){
        e.preventDefault();submit.click();
      }
    });
    new MutationObserver(counter).observe(editor,{attributes:true,attributeFilter:["disabled"]});
    counter();
  }
  wrapInput("style","музыкальный стиль","prepareText");
  wrapInput("lyrics","текст песни","generateQuick");
  wrapInput("songTopic","тему песни","generateLyrics");
  wrapInput("lyricStyle","стиль для текста","generateLyrics");

  // Native spring-check semantics are preserved; CSS only paints it.
  const own=$("studio34ConfirmOwn");
  if(own){
    own.addEventListener("change",()=>{
      const label=own.closest("label");
      label?.classList.toggle("micro36-confirmed",own.checked);
    });
  }

  // The track cover and vocal engine are not modified by the micro animation.
  // Job status updates arrive from the same /api/health polling as before.
  if(typeof window.call==="function")
    window.call("/api/health").then(h=>jobUpdate(h.job)).catch(()=>{});
})();
