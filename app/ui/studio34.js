"use strict";
/* Studio 3.4 interaction layer. Reuses existing local endpoints and model workflow. */
(() => {
  const $34=id=>document.getElementById(id);
  const mk=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=content;return e};
  let files=[], selected=null,selectedName="",inspectedName="",inspectorId=0;
  let playerIndex=-1;
  let savedFocus=null;
  const player=$34("studio34Audio");
  const panel=$34("studio34Inspector");
  // Primary action belongs to the composer, not beneath the song list.
  const composerAction=$34("generateQuick");
  $34("page-create").querySelector(".editor-panel").appendChild(composerAction);
  const order=()=>files.filter(f=>f&&f.name);
  const safeText=v=>String(v??"");
  const durationFmt=secs=>{
    const n=Math.max(0,Number(secs)||0);
    return Math.floor(n/60)+":"+String(Math.floor(n%60)).padStart(2,"0");
  };
  function artIndex(file) {
    const s=String(file?.name||file||"default");
    let h=0;for(let i=0;i<s.length;i++)h=((h*31)+s.charCodeAt(i))|0;
    return Math.abs(h)%5;
  }
  function setArt(node,file) {
    if(!node)return;
    node.dataset.art=String(artIndex(file));
    const symbol=node.querySelector("span");
    if(symbol)symbol.textContent="♫";
    const url=file?.cover_url || (file?.name ? "/api/cover/"+encodeURIComponent(file.name) : "");
    if (!url || node.dataset.artUrl===url) return;
    node.dataset.artUrl=url;
    node.classList.add("micro36-refine");
    node.dataset.coverPhase="loading";
    node.classList.remove("is-loaded");
    node.querySelector("img.studio35-cover-image")?.remove();
    const image=document.createElement("img");
    image.className="studio35-cover-image";
    image.alt="";
    image.decoding="async";
    image.loading=node.id==="studio34InspectorCover" ? "eager" : "lazy";
    image.addEventListener("load",()=>{
      node.classList.add("is-loaded");
      node.dataset.coverPhase="complete";
    },{once:true});
    image.addEventListener("error",()=>{
      node.classList.remove("is-loaded");
      node.dataset.coverPhase="error";
      image.remove();
    },{once:true});
    image.src=url;
    node.append(image);
  }
  function showStatus(file) {
    if(file.voice_check_status==="rejected"||file.voice_applied===false)
      return {text:"Твой голос не применён",cls:"problem"};
    if(file.voice_applied===true)return{text:"С твоим голосом",cls:""};
    return{text:"Готово",cls:""};
  }
  function selectedRowHighlight() {
    document.querySelectorAll(".studio34-track-row").forEach(row=>
      row.classList.toggle("selected",row.dataset.filename===(inspectedName||selectedName))
    );
  }
  function playTrack(file) {
    if(!file || !file.name)return;
    const changed=selectedName!==file.name || !player.src;
    if(changed){
      selectedName=file.name;
      playerIndex=order().findIndex(f=>f.name===file.name);
      player.src="/api/audio/"+encodeURIComponent(file.name);
      $34("studio34PlayerName").textContent=file.title||file.name;
      $34("studio34PlayerSub").textContent=file.when||"Мои композиции";
      setArt($34("studio34PlayerCover"),file);
      selectedRowHighlight();
    }
    if(player.paused){
      const promise=player.play();
      if(promise?.catch)promise.catch(()=>notify("Не удалось запустить песню. Проверь MP3.",true));
    }else player.pause();
  }
  function renderTime(){
    $34("studio34CurrentTime").textContent=durationFmt(player.currentTime);
    $34("studio34Duration").textContent=durationFmt(player.duration);
    const bar=$34("studio34Seek");
    if(!bar.matches(":active"))bar.value=String((Number.isFinite(player.duration)&&player.duration>0)?Math.round(player.currentTime/player.duration*1000):0);
  }
  function stepTrack(direction){
    if(!order().length)return;
    let n=playerIndex;
    if(n<0)n=direction>0?-1:0;
    n=(n+direction+order().length)%order().length;
    playTrack(order()[n]);
  }
  player.volume=0.85;
  $34("studio34PlayerPlay").addEventListener("click",()=>{
    if(!player.src){
      if(files.length)playTrack(files[0]);
      else notify("Сначала выбери песню.");
      return;
    }
    if(player.paused)player.play().catch(()=>notify("Не удалось воспроизвести трек.",true));
    else player.pause();
  });
  $34("studio34Prev").addEventListener("click",()=>stepTrack(-1));
  $34("studio34Next").addEventListener("click",()=>stepTrack(1));
  $34("studio34Seek").addEventListener("input",e=>{
    if(Number.isFinite(player.duration)&&player.duration>0)player.currentTime=Number(e.target.value)/1000*player.duration;
  });
  $34("studio34Volume").addEventListener("input",e=>{player.volume=Number(e.target.value);player.muted=false});
  player.addEventListener("play",()=>{
    $34("studio34PlayerPlay").textContent="Ⅱ";
    $34("studio34PlayerPlay").setAttribute("aria-label","Пауза");
    document.querySelectorAll("audio").forEach(a=>{if(a!==player&&!a.paused)a.pause()});
    selectedRowHighlight();
  });
  player.addEventListener("pause",()=>{
    $34("studio34PlayerPlay").textContent="▶";
    $34("studio34PlayerPlay").setAttribute("aria-label","Воспроизвести");
  });
  ["timeupdate","loadedmetadata","durationchange","seeking"].forEach(s=>player.addEventListener(s,renderTime));
  player.addEventListener("ended",()=>stepTrack(1));

  function makeTrackRow(file){
    const row=mk("article","studio34-track-row");
    row.dataset.filename=file.name;
    row.tabIndex=0;
    row.setAttribute("role","button");
    row.setAttribute("aria-label","Сведения о песне "+(file.title||file.name));
    const art=mk("div","studio34-cover");art.setAttribute("aria-hidden","true");art.append(mk("span","","♫"));
    setArt(art,file);
    const body=mk("div","studio34-track-main");
    body.append(mk("strong","",file.title||file.name),mk("small","",file.when||"Локальная запись"));
    if(file.style_preview){
      const preview=mk("span","studio37-style-preview",file.style_preview);
      preview.title=file.style_preview;
      body.append(preview);
    }
    const status=showStatus(file);
    body.append(mk("span","studio34-track-status"+(status.cls?" "+status.cls:""),status.text));
    const actions=mk("div","studio34-track-buttons");
    const play=mk("button","studio34-row-play","▶");
    play.type="button";play.setAttribute("aria-label","Воспроизвести "+(file.title||file.name));
    play.addEventListener("click",e=>{e.stopPropagation();playTrack(file)});
    const more=mk("button","studio34-row-menu","⋯");
    more.type="button";more.setAttribute("aria-label","Подробнее о треке");
    more.addEventListener("click",e=>{e.stopPropagation();openInspector(file)});
    actions.append(play,more);
    row.append(art,body,actions);
    row.addEventListener("click",()=>openInspector(file));
    row.addEventListener("keydown",e=>{
      if(e.target!==row)return;
      if(e.key==="Enter"||e.key===" "){e.preventDefault();openInspector(file)}
    });
    row.classList.toggle("selected",file.name===selectedName);
    row.classList.toggle("studio35-new",freshNames.has(file.name));
    return row;
  }
  window.studio34MakeTrackRow=makeTrackRow;

  function refreshFeedView(){
    const list=$34("studio34FeedList"),q=$34("studio34CreateSearch").value.trim().toLocaleLowerCase("ru");
    const found=files.filter(f=>!q||(String(f.title||"")+" "+f.name).toLocaleLowerCase("ru").includes(q));
    const sort=window.studio37FeedSort||"newest";
    if(sort==="oldest")found.sort((a,b)=>Number(a.mtime||0)-Number(b.mtime||0));
    else if(sort==="title")found.sort((a,b)=>String(a.title||a.name).localeCompare(String(b.title||b.name),"ru"));
    else found.sort((a,b)=>Number(b.mtime||0)-Number(a.mtime||0));
    list.replaceChildren();
    if(!found.length){list.append(mk("div","placeholder",files.length?"Ничего не найдено.":"Здесь появятся твои первые песни."));return;}
    let previousDate="";
    const today=new Date();
    const dateKey=d=>String(d.getDate()).padStart(2,"0")+"."+String(d.getMonth()+1).padStart(2,"0")+"."+d.getFullYear();
    const todayKey=dateKey(today);
    const yesterday=new Date(today.getFullYear(),today.getMonth(),today.getDate()-1);
    const yesterdayKey=dateKey(yesterday);
    found.slice(0,18).forEach(f=>{
      const date=String(f.when||"").slice(0,10);
      if(sort!=="title"&&date!==previousDate&&date){
        const label=date===todayKey?"Сегодня":date===yesterdayKey?"Вчера":date;
        list.append(mk("div","studio37-date-group",label));
        previousDate=date;
      }
      list.append(makeTrackRow(f));
    });
  }
  window.studio34RenderFeed=(tracks)=>{
    if(!Array.isArray(tracks))return;
    const was=selectedName;
    files=tracks.slice().sort((a,b)=>Number(b.mtime||0)-Number(a.mtime||0));
    playerIndex=order().findIndex(f=>f.name===was);
    refreshFeedView();selectedRowHighlight();
  };
  // Optimistically insert completed takes before any network refresh.
  // The following /api/tracks sync replaces this with authoritative mtime order.
  let freshNames=new Set();
  window.studio35RegisterGenerated=generated=>{
    if (!Array.isArray(generated) || !generated.length) return;
    freshNames=new Set(generated.map(f=>f.name));
    const known=new Set(freshNames);
    const latest=generated.slice().reverse().map(f=>({
      ...f,
      when:f.when || new Date().toLocaleString("ru-RU"),
      cover_url:f.cover_url || "/api/cover/"+encodeURIComponent(f.name),
      mtime:Date.now()/1000
    }));
    files=[...latest,...files.filter(f=>!known.has(f.name))];
    refreshFeedView();
    const pane=$34("page-create")?.querySelector(".results-panel");
    if(pane&&$34("page-create").classList.contains("visible"))
      pane.scrollTo({top:0,behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});
  };
  $34("studio34CreateSearch").addEventListener("input",refreshFeedView);
  $34("feedGoLibrary").addEventListener("click",()=>navigate("tracks"));
  window.studio34OnNavigate=page=>{
    if(page==="create"||page==="tracks")refreshTracks();
    if(page!=="create"&&page!=="tracks"&&panel.classList.contains("open"))closeInspector();
    if(page!=="voices"&&$34("studio34VoiceWizard").open)closeWizard();
  };

  async function copy(text){
    try{await navigator.clipboard.writeText(text);notify("Скопировано в буфер обмена.");}
    catch(e){
      const field=mk("textarea");field.value=text;field.style.position="fixed";field.style.opacity="0";
      document.body.appendChild(field);field.select();
      const ok=document.execCommand("copy");field.remove();
      notify(ok?"Скопировано.":"Не удалось скопировать текст.",!ok);
    }
  }
  const closeInspector=()=>{
    panel.classList.remove("open");panel.setAttribute("aria-hidden","true");
    $34("studio34InspectorBackdrop").hidden=true;
    selected=null;inspectedName="";selectedRowHighlight();
    if(savedFocus?.isConnected)savedFocus.focus({preventScroll:true});
    savedFocus=null;
  };
  window.studio34CloseInspector=closeInspector;
  window.studio36OnRemoved=name=>{
    if(selectedName===name){
      player.pause();player.removeAttribute("src");player.load();
      selectedName="";playerIndex=-1;
      $34("studio34PlayerName").textContent="Выбери песню";
      $34("studio34PlayerSub").textContent="Music Studio";
    }
    if(inspectedName===name)closeInspector();
  };
  $34("studio34InspectorClose").addEventListener("click",closeInspector);
  $34("studio34InspectorBackdrop").addEventListener("click",closeInspector);
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&panel.classList.contains("open")&&!$34("studio34VoiceWizard").open)closeInspector();
  });

  async function openInspector(file){
    if(!file?.name)return;
    selected=file;
    inspectedName=file.name;
    savedFocus=document.activeElement;
    panel.classList.add("open");panel.setAttribute("aria-hidden","false");
    $34("studio34InspectorBackdrop").hidden=false;
    $34("studio34InspectorTitle").textContent=file.title||file.name;
    $34("studio34InspectorDate").textContent=file.when||"Сохранено локально";
    setArt($34("studio34InspectorCover"),file);
    const state=showStatus(file);
    $34("studio34InspectorVoice").classList.toggle("problem",state.cls==="problem");
    $34("studio34InspectorVoice").textContent=state.text;
    $34("studio34InspectorStyle").textContent="Загружаем стиль…";
    $34("studio34InspectorLyrics").textContent="Загружаем текст…";
    $34("studio34InspectorStyle").classList.remove("expanded");
    $34("studio34InspectorLyrics").classList.remove("expanded");
    $34("studio34ExpandStyle").textContent="Развернуть ↓";
    $34("studio34ExpandLyrics").textContent="Развернуть ↓";
    $34("studio34InspectorDownload").href="/api/audio/"+encodeURIComponent(file.name);
    $34("studio34InspectorDownload").download=file.name;
    const more=$34("studio34InspectorMore");more.replaceChildren();
    if(file.master_url){
      const x=mk("a","studio34-ghost-button","↓ WAV-мастер");
      x.href="/api/master/"+encodeURIComponent(file.name.replace(/\.mp3$/i,".wav"));
      x.download=file.name.replace(/\.mp3$/i,".wav");more.append(x);
    }
    if(file.original_url&&file.original_name){
      const x=mk("a","studio34-ghost-button","↓ Исходная версия");
      x.href=file.original_url.slice(0,file.original_url.lastIndexOf("/")+1)+encodeURIComponent(file.original_name);
      x.download=file.original_name;more.append(x);
    }
    const id=++inspectorId;
    selectedRowHighlight();
    try{
      const info=await call("/api/track_details?name="+encodeURIComponent(file.name));
      if(id!==inspectorId||!selected||selected.name!==file.name)return;
      $34("studio34InspectorTitle").textContent=info.title||file.title||file.name;
      $34("studio34InspectorStyle").textContent=info.style_original||info.model_caption||"Промпт этого трека не сохранился.";
      $34("studio34InspectorLyrics").textContent=info.lyrics_original||info.lyrics_sent||"Для этого трека текст не сохранился.";
    }catch(e){if(id===inspectorId){$34("studio34InspectorStyle").textContent="Описание недоступно: "+e.message;$34("studio34InspectorLyrics").textContent="Текст не удалось загрузить."}}
    panel.focus({preventScroll:true});
  }
  window.studio34OpenInspector=openInspector;
  $34("studio34InspectorPlay").addEventListener("click",()=>{if(selected)playTrack(selected)});
  $34("studio34CopyStyle").addEventListener("click",()=>copy($34("studio34InspectorStyle").textContent));
  $34("studio34CopyLyrics").addEventListener("click",()=>copy($34("studio34InspectorLyrics").textContent));
  for(const [button,content] of [["studio34ExpandStyle","studio34InspectorStyle"],["studio34ExpandLyrics","studio34InspectorLyrics"]]){
    $34(button).addEventListener("click",()=>{
      const expanded=$34(content).classList.toggle("expanded");
      $34(button).textContent=expanded?"Свернуть ↑":"Развернуть ↓";
    });
  }
  $34("studio34InspectorDelete").addEventListener("click",async()=>{
    if(!selected)return;
    const file=selected;
    if(window.studio36DeleteTrack){
      await window.studio36DeleteTrack(file);
      return;
    }
    if(!confirm("Убрать «"+(file.title||file.name)+"» из библиотеки?\n\nMP3 будет перемещён в локальную папку «Корзина треков», остальные файлы и голосовые записи сохранятся."))return;
    const removeButton=$34("studio34InspectorDelete");removeButton.disabled=true;
    try{
      await call("/api/remove_track",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:file.name})});
      if(selectedName===file.name){player.pause();player.removeAttribute("src");player.load();selectedName="";$34("studio34PlayerName").textContent="Выбери песню"}
      closeInspector();await refreshTracks();notify("Трек перемещён в локальную корзину.");
    }catch(e){notify(e.message,true)}
    finally{removeButton.disabled=false}
  });

  // Voice wizard: the existing PCM recorder remains the only recording implementation.
  const wizard=$34("studio34VoiceWizard");
  const rec=$34("voiceRecorder"),importZone=$34("voiceDrop"),uploadStatus=$34("uploadStatus"),recPreview=$34("recordPreview");
  $34("studio34RecorderSlot").append(rec);
  $34("studio34ImportSlot").append(importZone);
  $34("studio34ImportStatusSlot").append(uploadStatus);
  const wizardPlayback=mk("audio");
  wizardPlayback.controls=true;
  wizardPlayback.preload="metadata";
  wizardPlayback.setAttribute("aria-label","Прослушать запись перед подтверждением");
  $34("studio34ConfirmPreview").append(wizardPlayback);
  let step=1,language="ru",mode="sing",lastScript="",readyRecording=false,uploaded=false;
  const scripts={
    ru:{
      sing:[
        "Сквозь облака пробился свет,\nИ новый день подарит след.\nПускай звучат мои слова,\nВ них оживает жизнь сама.",
        "Над тихой речкой тает снег,\nУходит вдаль знакомый след.\nЯ запою среди огней,\nИ мир становится теплей.",
        "Снова ветер зовёт с собой,\nНад дорогой вечер золотой.\nСветят звёзды в глубине,\nЭта песня живёт во мне.",
        "Море дышит, берег ждёт,\nТёплый ветер нас зовёт.\nПесня льётся без преград,\nЯ встречаю новый взгляд."
      ],
      read:[
        "Сегодня я записываю свой голос. Говорю спокойно, разборчиво и без спешки. За окном начинается утро. Я делаю короткую паузу и продолжаю.",
        "Это мой настоящий голос. Я читаю несколько предложений в обычной манере. В комнате тихо, а на улице слышен ветер. Теперь я заканчиваю запись.",
        "Я люблю слушать музыку в дороге. Иногда она напоминает о важных встречах, а иногда помогает собраться с мыслями. Я говорю естественно и без напряжения."
      ]
    },
    en:{
      sing:[
        "Morning light upon the sea,\nEvery sound is calling me.\nLet the rhythm lead the way,\nI will sing another day.",
        "Far beyond the city glow,\nWhere the gentle rivers flow.\nHear the melody tonight,\nEverything will feel alright.",
        "Underneath the golden sky,\nI can hear the reasons why.\nWhen the morning starts to shine,\nEvery song will feel like mine."
      ],
      read:[
        "This is my natural speaking voice. I am reading at a comfortable pace. The room is quiet, and I can hear the rain outside. I will finish this recording now.",
        "Today I am making a voice recording. I speak clearly, with ordinary pauses and a relaxed tone. My voice sounds natural when I am not rushing.",
        "Music makes every journey different. Some songs bring back memories, and others give me the energy to start something new. This is my own voice."
      ]
    }
  };
  function chooseNewScript(){
    const options=scripts[language][mode];
    const remaining=options.filter(s=>s!==lastScript);
    lastScript=remaining[Math.floor(Math.random()*remaining.length)]||options[0];
    $34("studio34VoiceScript").textContent=lastScript;
    $34("studio34VoiceScriptMini").textContent=lastScript;
  }
  function savedLevel(){
    return $34("studio34VocalLevels").querySelector('input[name="studio34Level"]:checked')?.value||"novice";
  }
  function setWizardStep(n){
    step=Math.min(4,Math.max(1,n));
    $34("studio34StepNumber").textContent=String(step);
    wizard.querySelectorAll("[data-wizard-step]").forEach(e=>e.classList.toggle("hidden",Number(e.dataset.wizardStep)!==step));
    wizard.querySelectorAll(".studio34-wizard-progress i").forEach((e,i)=>e.classList.toggle("active",i<step));
    $34("studio34WizardBack").disabled=step===1;
    $34("studio34WizardNext").textContent=step===4?"Сохранить профиль":"Продолжить →";
    $34("studio34WizardStatus").textContent=step===2?"Для лучшего качества запиши хотя бы 10 секунд.":step===3?"Запись можно прослушать или загрузить свой файл.":step===4?"Уровень — подсказка профиля, не обработка аудио.":"";
    wizard.scrollTo({top:0,behavior:"instant"});
  }
  function openWizard(){
    language="ru";mode="sing";readyRecording=false;uploaded=false;
    $34("studio34VoiceLanguage").value="ru";
    $34("studio34ConfirmOwn").checked=false;
    wizard.querySelectorAll("[data-voice-mode]").forEach(e=>e.classList.toggle("active",e.dataset.voiceMode==="sing"));
    chooseNewScript();setWizardStep(1);
    if(!wizard.open)wizard.showModal();
    $34("studio34VoiceLanguage").focus();
  }
  function closeWizard(){
    if($34("recordStop").disabled===false){
      $34("recordStop").click();
    }
    if(!wizard.open)return;
    wizard.close();
    if(!recPreview.paused)recPreview.pause();
    if(!wizardPlayback.paused)wizardPlayback.pause();
  }
  window.studio34OpenVoiceWizard=openWizard;
  $34("studio34NewVoice").addEventListener("click",openWizard);
  $34("studio34WizardClose").addEventListener("click",closeWizard);
  wizard.addEventListener("cancel",e=>{e.preventDefault();closeWizard()});
  $34("studio34VoiceLanguage").addEventListener("change",e=>{language=e.target.value;chooseNewScript()});
  wizard.querySelectorAll("[data-voice-mode]").forEach(button=>button.addEventListener("click",()=>{
    mode=button.dataset.voiceMode;
    wizard.querySelectorAll("[data-voice-mode]").forEach(b=>b.classList.toggle("active",b===button));
    chooseNewScript();
  }));
  $34("studio34NewVoiceScript").addEventListener("click",chooseNewScript);
  $34("studio34WizardBack").addEventListener("click",()=>setWizardStep(step-1));
  function saveProfileMetadata(){
    const n=typeof selectedVoice==="string"&&selectedVoice?selectedVoice:$34("voiceSelect").value;
    if(!n)return;
    const value={level:savedLevel(),language,mode,updated:new Date().toISOString()};
    try{localStorage.setItem("studio34.profile."+n,JSON.stringify(value))}catch(_){}
  }
  function acceptRecording(){
    if(!recPreview.src||recPreview.classList.contains("hidden")){
      $34("studio34WizardStatus").textContent="Запиши голос на предыдущем шаге или загрузи готовый файл.";
      return false;
    }
    readyRecording=true;
    wizardPlayback.src=recPreview.src;
    wizardPlayback.load();
    return true;
  }
  $34("studio34WizardNext").addEventListener("click",async()=>{
    if(step===1)return setWizardStep(2);
    if(step===2){
      if($34("recordStop").disabled===false){
        $34("studio34WizardStatus").textContent="Сначала останови запись.";
        return;
      }
      acceptRecording();
      return setWizardStep(3);
    }
    if(step===3){
      if(!$34("studio34ConfirmOwn").checked){
        $34("studio34WizardStatus").textContent="Подтверди, что эта запись принадлежит тебе.";
        return;
      }
      if(!acceptRecording()&&!uploaded){
        $34("studio34WizardStatus").textContent="Нужна запись с микрофона или выбранный файл.";
        return;
      }
      return setWizardStep(4);
    }
    if(!$34("studio34ConfirmOwn").checked){
      setWizardStep(3);$34("studio34WizardStatus").textContent="Подтверди право использовать запись.";
      return;
    }
    if(uploaded){
      saveProfileMetadata();closeWizard();
      await refreshVoices();
      notify("Запись добавлена в твои голосовые профили.");
      return;
    }
    if(readyRecording&&!recPreview.classList.contains("hidden")){
      $34("studio34WizardNext").disabled=true;
      $34("studio34WizardStatus").textContent="Сохраняем WAV на компьютере…";
      $34("recordUse").click(); // Existing, proven PCM upload workflow.
    }
  });
  // Prevent accidental uploading of a voice without ownership confirmation.
  $34("voiceFile").disabled=true;
  $34("studio34ConfirmOwn").addEventListener("change",e=>{
    $34("voiceFile").disabled=!e.target.checked;
  });
  // Uploaded files are saved by the existing handler and the wizard adds profile metadata.
  new MutationObserver(()=>{
    if(!wizard.open)return;
    const text=uploadStatus.textContent.trim();
    if(text.startsWith("✓ Загружено:")){
      uploaded=true;$34("studio34WizardStatus").textContent="Аудиофайл загружен. Теперь выбери уровень вокала.";
      setWizardStep(4);
    }
  }).observe(uploadStatus,{childList:true,subtree:true,characterData:true});
  new MutationObserver(()=>{
    if(!wizard.open)return;
    if(recPreview.src&&!recPreview.classList.contains("hidden")){
      readyRecording=true;
      wizardPlayback.src=recPreview.src;
    }
  }).observe(recPreview,{attributes:true,attributeFilter:["class","src"]});
  new MutationObserver(()=>{
    const st=$34("recordStatus").textContent;
    if(wizard.open&&st.startsWith("Сохранено:")){
      saveProfileMetadata();$34("studio34WizardNext").disabled=false;closeWizard();
    }else if(wizard.open&&st.startsWith("Ошибка")){
      $34("studio34WizardNext").disabled=false;$34("studio34WizardStatus").textContent=st;
    }
  }).observe($34("recordStatus"),{childList:true,subtree:true});
  // Keep preview seek exact, but simplify the temporary wizard player controls.
  wizardPlayback.volume=0.85;
  const levelTitles={novice:"Не умею петь",beginner:"Начинающий",confident:"Уверенный",professional:"Профессионал"};
  const voiceList=$34("voicesList");
  function labelVoiceProfiles(){
    voiceList.querySelectorAll(".asset-row").forEach(row=>{
      const name=row.querySelector(".asset-meta b")?.textContent.trim();
      if(!name)return;
      let meta;try{meta=JSON.parse(localStorage.getItem("studio34.profile."+name)||"null")}catch(_){}
      let badge=row.querySelector(".studio34-level-badge");
      if(meta?.level){
        if(!badge){badge=mk("span","studio34-level-badge");row.querySelector(".asset-meta")?.append(badge)}
        badge.textContent=(meta.language==="en"?"EN":"RU")+" · "+(levelTitles[meta.level]||"Профиль")+" · "+(meta.mode==="read"?"Речь":"Пение");
      }else badge?.remove();
    });
  }
  new MutationObserver(labelVoiceProfiles).observe(voiceList,{childList:true});
  labelVoiceProfiles();
  refreshTracks();
})();
