"use strict";
/* Music Studio 5.0 • unified application, existing local generation engine and audio files */
(() => {
 const $=id=>document.getElementById(id);
 const ico=n=>'<svg class="ico" aria-hidden="true"><use href="#i-'+n+'"></use></svg>';
 const e=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
 const clamp=(v,a,b)=>Math.min(b,Math.max(a,v));
 const fmt=n=>{n=Number(n);if(!Number.isFinite(n)||n<0)n=0;return Math.floor(n/60)+":"+String(Math.floor(n%60)).padStart(2,"0")};
 const store=(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(_){}};
 const getStore=(k,def)=>{try{const x=JSON.parse(localStorage.getItem(k));return x??def}catch(_){return def}};
 const first=(o,props)=>{for(const k of props)if(o&&o[k]!=null)return o[k];return null};
 const state={
  view:"create",tracks:[],voices:[],fav:getStore("musicStudio.favorites43",{}),sort:"new",recentFilter:"all",libraryFilter:"all",selectedVoice:getStore("studio50.voice",""),useVoice:!!getStore("studio50.useVoice",false),useGrooveRef:!!getStore("studio90.grooveReference",false),duration:Number(getStore("studio50.duration",0)),bpm:Number(getStore("studio50.bpm",0)),twoVersions:!!getStore("studio50.two",true),instrumental:false,playing:null,lastCompleted:"",job:null,loadLimit:40,inspected:null,voiceAudio:null,voiceMedia:null,playingVoiceName:"",
  melody:{kind:"hum",file:null,blob:null,url:"",source:"",voiceFile:"",duration:0,notes:[],recorded:false,usingMic:false},
  lyricsBusy:false,modalStep:1,voiceDraft:{blob:null,name:"",url:""},
  shuffle:false,repeat:false,autoTitle:true
 };
 let noticeTimer,toastFn=null,healthBusy=false,statusPoll=0,lyricsPoll=0;
 function toast(message,kind="",undo){
  const root=$("toast");root.className="toast"+(kind==="error"?" error":"");root.textContent=String(message);
  if(undo){const btn=document.createElement("button");btn.textContent="Вернуть";btn.addEventListener("click",async()=>{try{await undo();root.hidden=true}catch(ex){toast(ex.message,"error")}});root.append(btn)}
  root.hidden=false;clearTimeout(noticeTimer);noticeTimer=setTimeout(()=>root.hidden=true,undo?11000:(kind==="error"?17000:4800))
 }
 const json=async(path,options={})=>{
  let r;
  try{r=await fetch(path,{cache:"no-store",...options})}
  catch(err){
   if(location.protocol==="file:")throw Error("Music Studio нельзя запускать двойным кликом по HTML. Открой http://127.0.0.1:7870 после запуска Start-MusicStudio.ps1.");
   if(err?.name==="AbortError")throw Error("Локальный сервер не ответил вовремя. Проверь scripts/Diagnose-Windows.ps1.");
   // Never silently retry a POST /api/generate: the job may already have started.
   throw Error("Нет связи с сервером Music Studio (127.0.0.1:7870). "
    +"Возможно, он остановился или закончилась память при загрузке ACE-Step. "
    +"Проверь http://127.0.0.1:7870/api/health и запусти scripts/Diagnose-Windows.ps1.");
  }
  const t=await r.text();let data;try{data=JSON.parse(t)}catch{throw Error("Сервер вернул некорректный ответ HTTP "+r.status+". Проверь scripts/Diagnose-Windows.ps1.")}
  if(!r.ok)throw Error(data.error||data.message||("Ошибка HTTP "+r.status));
  return data;
 };
 const post=(path,data)=>json(path,{method:"POST",headers:{"Content-Type":"application/json;charset=utf-8"},body:JSON.stringify(data)});
 const upload=async(file,kind)=>{
  if(!file)throw Error("Выбери файл");
  if(file.size>88*1048576)throw Error("Размер файла больше 88 МБ");
  const name=file.name||("recording_"+Date.now()+".wav");
  return json("/api/upload?kind="+encodeURIComponent(kind)+"&name="+encodeURIComponent(name),{
   method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file});
 };
 const audio=$("mainAudio"),playerTitle=$("playerTitle");
 audio.volume=Number(getStore("studio50.volume",.85));$("volume").value=String(audio.volume);
 function view(name){
  if(!["create","melody","voices","library","settings"].includes(name))return;
  state.view=name;document.querySelectorAll(".view").forEach(x=>x.classList.toggle("visible",x.id==="view-"+name));
  document.querySelectorAll("[data-view].nav-link").forEach(x=>x.classList.toggle("active",x.dataset.view===name));
  const titles={create:"Создать трек",melody:"Студия мелодий",voices:"Мой голос",library:"Библиотека",settings:"Настройки"};
  $("bread").textContent=titles[name];
  if(name==="library")renderLibrary();
  if(name==="voices")renderVoices();
  if(name==="settings")loadSettings();
  if(name==="melody")renderMelody();
  try{document.querySelector("#main .view.visible").scrollTop=0}catch(_){}
 }
 document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>view(b.dataset.view)));
 function persistComposer(){
  store("studio50.draft",{title:$("songName").value,lyrics:$("songWords").value,style:$("songStyle").value,melodyWords:$("melodyWords").value,melodyStyle:$("melodyStyle").value,melodyName:$("melodyName").value});
 }
 const prevDraft=getStore("studio50.draft",{});
 for(const [id,key] of [["songName","title"],["songWords","lyrics"],["songStyle","style"],["melodyWords","melodyWords"],["melodyStyle","melodyStyle"],["melodyName","melodyName"]]){
  if(typeof prevDraft[key]==="string")$(id).value=prevDraft[key];
  $(id).addEventListener("input",()=>{persistComposer();updateCount()});
 }
 const genres={
  pop:"Современный русский поп, выразительный мелодичный вокал, запоминающийся припев, воздушные синтезаторы, чистый бас, динамичные барабаны, профессиональное сведение.",
  rock:"Мощный современный поп-рок, настоящая электрогитара, плотный бас, энергичные живые барабаны, выразительные вокальные гармонии, яркий припев и динамичный мастеринг.",
  trap:"Contemporary melodic trap, deep tuned 808 bass, punchy kick, dry snare, clean hi-hats, spacious keys, memorable musical hook, controlled sub and crisp radio-ready mix.",
  club:"Клубная электронная танцевальная музыка, плотная бочка, живой бас, современные синтезаторы, цепкий хук, атмосферные брейки и яркий энергичный дроп."
 };
 document.querySelectorAll("[data-preset]").forEach(b=>b.addEventListener("click",()=>{$("songStyle").value=genres[b.dataset.preset];updateCount();persistComposer()}));
 function updateCount(){
  $("titleCount").textContent=$("songName").value.length+" / 120";
  $("styleCount").textContent=$("songStyle").value.length+" символов";
  $("wordsCount").textContent=($("songWords").value.replace(/\[[^\]]*]/g," ").trim().split(/\s+/).filter(Boolean).length||0)+" слов";
 }
 updateCount();
 function expandField(id){const x=$(id);const toggle=x.dataset.maximized==="1";x.dataset.maximized=toggle?"0":"1";x.style.height=toggle?"":(id==="songWords"?"460px":"290px");x.focus()}
 $("expandWords").addEventListener("click",()=>expandField("songWords"));$("expandStyle").addEventListener("click",()=>expandField("songStyle"));
 async function copy(txt){try{await navigator.clipboard.writeText(txt);toast("Скопировано")}catch{toast("Не удалось скопировать","error")}}
 $("copyWords").addEventListener("click",()=>copy($("songWords").value));$("copyStyle").addEventListener("click",()=>copy($("songStyle").value));
 $("styleHelp").addEventListener("click",()=>toast($("styleHelp").title));
 function setInstrumental(on){state.instrumental=on;$("songMode").classList.toggle("active",!on);$("instrumentMode").classList.toggle("active",on);$("songWords").disabled=on;$("songWords").placeholder=on?"Инструментал: текст не обязателен.":"[Intro — мягкая гитара]\nНачни писать свою песню…";}
 $("songMode").addEventListener("click",()=>setInstrumental(false));$("instrumentMode").addEventListener("click",()=>setInstrumental(true));
 async function loadTracks(){
  try{
   const res=await json("/api/tracks");state.tracks=Array.isArray(res.tracks)?res.tracks.slice().sort((a,b)=>Number(b.mtime||0)-Number(a.mtime||0)):[];
   renderRecent();renderLibrary();renderMelodyResults();
  }catch(err){toast("Библиотека: "+err.message,"error")}
 }
 async function loadVoices(){
  try{const r=await json("/api/voices");state.voices=(r.voices||[]);
   if(state.selectedVoice&&!state.voices.some(x=>x.name===state.selectedVoice)){state.selectedVoice="";state.useVoice=false}
   const options='<option value="">Без голоса исполнителя</option>'+state.voices.map(v=>'<option value="'+e(v.name)+'">'+e(v.artist_name?v.artist_name+" — "+v.name:v.name)+'</option>').join("");
   $("voiceSelect").innerHTML=options;$("voiceSelect").value=state.selectedVoice;$("useVoice").checked=state.useVoice;
   renderVoiceChip();renderVoices();
  }catch(ex){toast("Голос: "+ex.message,"error")}
 }
 function renderVoiceChip(){
  const chosen=state.useVoice&&state.selectedVoice;
  const selectedMeta=state.voices.find(v=>v.name===state.selectedVoice);
  const shortSample=!!(chosen&&selectedMeta&&Number(selectedMeta.recording_seconds)>0&&Number(selectedMeta.recording_seconds)<15);
  $("voiceChip").classList.toggle("off",!chosen);$("voiceChip").querySelector("span").textContent=chosen?(selectedMeta?.profile_id?"✓ Мой голос · профиль":"⚠ Голос · базовая модель"):(state.selectedVoice?"⚠ Мой голос отключён":"Без моего голоса");
  $("useVoice").checked=state.useVoice;$("voiceSelect").value=state.selectedVoice;
  $("voiceNotice").classList.toggle("has-voice",!!chosen);
  $("voiceNoticeTitle").textContent=shortSample?"⚠ Запись голоса слишком короткая":chosen?(selectedMeta?.profile_id?"Голос привязан к профилю":"⚠ Используется базовая модель"):state.selectedVoice?"⚠ Голос выбран, но применение выключено":"Голос не выбран";
  $("voiceNoticeDescription").textContent=shortSample?"Длина "+Number(selectedMeta.recording_seconds).toFixed(1)+" с. Для качественного переноса полезен более длинный образец.":chosen?(selectedMeta?.profile_id?"Запись связана с подтверждённым профилем. Личную модель проверяет сервер перед генерацией; естественность нельзя гарантировать.":"Эта запись не привязана к профилю: применяется базовая Seed-VC вместо твоей персональной модели. Выбери привязанную запись в разделе «Мой голос»."):state.selectedVoice?"Запись сохранена, но в следующей песне не будет использован твой тембр. Включи переключатель в параметрах.":"Выбери запись, чтобы использовать свой тембр в новой песне.";
  store("studio50.voice",state.selectedVoice);store("studio50.useVoice",state.useVoice);
 }
 $("voiceChip").addEventListener("click",()=>openParams("voice"));
 $("openVoiceFromCreate").addEventListener("click",()=>openParams("voice"));
 $("openSettingsFromCreate").addEventListener("click",()=>openParams("time"));
 function openDialog(id){const x=$(id);if(!x.open)x.showModal()}
 function closeDialog(id){const x=$(id);if(x.open)x.close()}
 document.querySelectorAll("[data-close]").forEach(b=>b.addEventListener("click",()=>closeDialog(b.dataset.close)));
 for(const id of ["paramsDialog","voiceDialog","lyricsDialog"]){$(id).addEventListener("click",ev=>{if(ev.target===$(id))closeDialog(id)})}
 function openParams(tab="voice"){
  openDialog("paramsDialog");$("paramsVoiceTab").classList.toggle("active",tab==="voice");$("paramsTimeTab").classList.toggle("active",tab==="time");
  $("paramsVoice").hidden=tab!=="voice";$("paramsTime").hidden=tab!=="time";
  $("durationSelect").value=String(state.duration);$("bpmInput").value=String(state.bpm);$("twoVariants").checked=state.twoVersions;$("grooveReference").checked=state.useGrooveRef;
 }
 $("paramsVoiceTab").addEventListener("click",()=>openParams("voice"));$("paramsTimeTab").addEventListener("click",()=>openParams("time"));
 $("useVoice").addEventListener("change",ev=>{if(ev.target.checked&&!state.selectedVoice){ev.target.checked=false;toast("Сначала выбери запись голоса из списка.","error");return}state.useVoice=ev.target.checked;renderVoiceChip();renderVoices()});
 $("voiceSelect").addEventListener("change",ev=>{state.selectedVoice=ev.target.value;state.useVoice=!!state.selectedVoice;renderVoiceChip();renderVoices()});
 document.addEventListener("studioProfiles34:updated",()=>loadVoices());
 $("durationSelect").addEventListener("change",ev=>{state.duration=Number(ev.target.value)||0;store("studio50.duration",state.duration)});
 $("bpmInput").addEventListener("change",ev=>{state.bpm=Number(ev.target.value)||0;store("studio50.bpm",state.bpm)});
 $("twoVariants").addEventListener("change",ev=>{state.twoVersions=ev.target.checked;store("studio50.two",state.twoVersions);$("createButton").lastChild.textContent="" ;$("createButton").innerHTML=ico("spark")+" Создать "+(state.twoVersions?"2 варианта":"1 вариант")});
 $("grooveReference").addEventListener("change",ev=>{state.useGrooveRef=ev.target.checked;store("studio90.grooveReference",state.useGrooveRef);toast(state.useGrooveRef?"Экспериментальный ритм 808 включён":"Генерируем строго по твоему музыкальному описанию")});
 $("durationSelect").value=String(state.duration);$("bpmInput").value=String(state.bpm);$("twoVariants").checked=state.twoVersions;
 $("voiceConfig").addEventListener("click",()=>openParams("voice"));
 $("voiceRecordInParams").addEventListener("click",()=>{closeDialog("paramsDialog");openVoiceWizard()});
 $("openMelodyFromCreate").addEventListener("click",()=>view("melody"));
 async function generateTrack(data,tag="create"){
  if(!data.style?.trim())return toast("Укажи музыкальный стиль","error"),false;
  if(!data.instrumental&&!data.lyrics?.trim())return toast("Добавь текст или выбери инструментал","error"),false;
  if(data.use_voice&&!data.voice)return toast("Сначала выбери голосовую запись","error"),false;
  if(data.voice&&!data.use_voice&&!data.instrumental&&!confirm("Голосовая запись выбрана, но применение МОЕГО ГОЛОСА выключено. Создать трек без переноса твоего тембра?"))return false;
  // The server is authoritative for the selected checkpoint. A profile
  // label alone is not proof that its personalized weights are available.
  if(data.mode==="remix"&&!data.source)return toast("Для аранжировки нужен исходный аудиофайл","error"),false;
  if(data.bpm&&(data.bpm<30||data.bpm>300))return toast("Темп должен быть 30–300 BPM либо 0","error"),false;
  const h=state.job;if(h&&["preparing","generating","converting"].includes(h.status))return toast("Уже идёт генерация","error"),false;
  try{
   $("createButton").disabled=true;$("melodyGenerate").disabled=true;
   // PREPARE runs the exact routing policy before spending GPU time.
   const preview=await post("/api/prepare",data);
   if(data.use_trained_groove_reference && preview.groove_reference?.available===false){
    data.use_trained_groove_reference=false;
    state.useGrooveRef=false;
    store("studio90.grooveReference",false);
    $("grooveReference").checked=false;
    toast("Обученный 808-грув отсутствует. Продолжаем обычную генерацию ACE-Step без него.","error");
   }
   if(data.use_voice&&!data.instrumental&&!preview.voice_model_preview?.trained){
    const routing=preview.voice_model_preview;
    const fallback=routing?.model||"base_SeedVC";
    if(!confirm("ВНИМАНИЕ: выбранный референс НЕ использует персональную обученную модель.\nМаршрут: "+fallback+".\nГолос может быть совсем не похож на твой.\nСгенерировать с базовой моделью?")){
     $("createButton").disabled=false;updateMelodyButton();
     toast("Генерация отменена: выбери запись с персональным профилем.");
     return false;
    }
   }
   await post("/api/generate",data);
   state.lastCompleted="";state.job={status:"preparing",message:"Подготавливаем музыку…",files:[],id:"initial"};
   refreshJobUI();toast(tag==="melody"?"Аранжировка запущена":"Генерация запущена");
   return true;
  }catch(err){toast(err.message,"error");$("createButton").disabled=false;updateMelodyButton();return false}
 }
 $("createButton").addEventListener("click",async()=>{
  const data={title:$("songName").value.trim(),style:$("songStyle").value.trim(),lyrics:$("songWords").value.trim(),
   bpm:state.bpm,duration:state.duration,instrumental:state.instrumental,vocal_language:"auto",vocal_gender:"auto",
   mode:"new",source:"",quality:"composer",use_voice:state.useVoice,voice:state.selectedVoice,
   use_trained_groove_reference:state.useGrooveRef,
   voice_profile_id:state.voices.find(v=>v.name===state.selectedVoice)?.profile_id||"",apply_voice:true,
   trained_voice:false,voice_register:"auto",russian_rap:false,planner:true,producer:true,two_versions:state.twoVersions};
  await generateTrack(data);
 });
 async function checkHealth(){
  if(healthBusy)return;healthBusy=true;
  try{
   const h=await json("/api/health");
   state.job=h.job||{status:"idle"};
   state.lyricsBusy=!!h.lyrics_busy;
   const engine=h.engine||{status:h.ready?"connected":"starting",message:""};
   const status=$("engineStatus");status.classList.toggle("offline",["error","missing"].includes(engine.status));
   const label=engine.status==="connected"?"ACE-Step доступен":engine.status==="starting"?"Инициализация ACE-Step…":engine.status==="missing"?"ACE-Step не установлен":engine.status==="error"?"Ошибка запуска ACE-Step":"Ожидаем ACE-Step";
   status.replaceChildren(document.createElement("i"),document.createTextNode(" "+label));
   status.title=engine.message||label;
   $("settingsModel").textContent=engine.message||label;
   if(h.groove_reference){
    const control=$("grooveReference"),available=!!h.groove_reference.available;
    control.disabled=!available;
    control.title=h.groove_reference.message||"";
    const hint=control.closest(".toggle-line")?.querySelector("small");
    if(hint){
     if(!hint.dataset.originalText)hint.dataset.originalText=hint.textContent;
     hint.textContent=available?hint.dataset.originalText:"Недоступно: локальная модель groove23 не установлена. Рэп и бас 808 работают через ACE-Step без неё.";
    }
    if(!available && state.useGrooveRef){
     state.useGrooveRef=false;control.checked=false;
     store("studio90.grooveReference",false);
     toast("Экспериментальный 808-грув отключён: отсутствует необязательная обученная модель.");
    }
   }
   $("settingsLastJob").textContent=String(h.job?.status||"—");
   refreshJobUI();
   if(["error","missing"].includes(engine.status)&&!["generating","converting"].includes(state.job?.status)){
    $("feedJob").hidden=false;
    $("feedJob").classList.remove("processing");
    $("feedJob").textContent=engine.message+" Запусти scripts/Diagnose-Windows.ps1 для диагностики.";
   }
   if(h.job?.status==="done"&&h.job?.id&&state.lastCompleted!==h.job.id){
    state.lastCompleted=h.job.id;if(h.job.files?.length){await loadTracks();toast("Новые треки добавлены в начало списка")}
   }
  }catch(ex){$("engineStatus").classList.add("offline");$("engineStatus").replaceChildren(document.createElement("i"),document.createTextNode(" Нет подключения к Music Studio"));$("engineStatus").title=ex.message||"Сервер не отвечает";$("settingsModel").textContent=ex.message||"Сервер не отвечает"}
  finally{healthBusy=false}
 }
 function refreshJobUI(){
  const h=state.job||{status:"idle"},busy=["preparing","generating","converting"].includes(h.status);
  $("createButton").disabled=busy;$("melodyGenerate").disabled=busy||!state.melody.file;
  const title=busy?({"preparing":"Подготовка музыки","generating":"Создаём композицию","converting":"Переносим тембр"}[h.status]||"Генерация"):h.status==="error"?"Ошибка генерации":"";
  $("topJob").hidden=!busy;$("topJob").textContent=title;
  $("feedJob").hidden=!busy&&h.status!=="error";
  $("feedJob").classList.toggle("processing",busy);
  $("feedJob").textContent=busy?(" "+(h.message||title)):h.status==="error"?(h.error||"Ошибка генерации"):"";
  $("melodyStatus").textContent=busy?(h.message||"Генерация…"):state.melody.file?"Можно создавать аранжировку.":"Сначала запиши или загрузи мелодию.";
 }
 $("checkHealth").addEventListener("click",checkHealth);
 // Tracks: real files, real covers, native MP3 playback.
 const trackMap=()=>new Map(state.tracks.map(t=>[t.name,t]));
 const selectedFile=()=>state.playing?state.tracks.find(t=>t.name===state.playing):null;
 const fav=x=>!!state.fav[x];
 function saveFavorites(){store("musicStudio.favorites43",state.fav)}
 const art=f=>f.cover_url||("/api/cover/"+encodeURIComponent(f.name));
 function genre(f){
  const s=String(f.style_preview||"").toLowerCase();
  if(/pop.rock|поп.рок/.test(s))return"Поп-рок";
  if(/\brock\b|рок/.test(s))return"Рок";
  if(/\btrap\b|808/.test(s))return"Trap";
  if(/rap|рэп|хип.хоп/.test(s))return"Рэп";
  if(/club|dance|house|клуб/.test(s))return"Электроника";
  if(/pop|поп/.test(s))return"Поп";
  return"Музыка"
 }
 function shortDate(f){return String(f.when||"").split(" ")[0]||""}
 const durCache=new Map();const durationRequest=new Map();
 function fetchDuration(f){
  if(durCache.has(f.name)||durationRequest.has(f.name))return;
  const sample=new Audio();sample.preload="metadata";sample.src="/api/audio/"+encodeURIComponent(f.name);
  durationRequest.set(f.name,sample);
  const cleanup=()=>{
   if(Number.isFinite(sample.duration)&&sample.duration>0){
    durCache.set(f.name,fmt(sample.duration));
    document.querySelectorAll("[data-track]").forEach(row=>{
     if(row.dataset.track===f.name)row.querySelector(".track-duration")&&(row.querySelector(".track-duration").textContent=fmt(sample.duration));
    });
   }
   sample.removeAttribute("src");sample.load();durationRequest.delete(f.name);
  };
  sample.addEventListener("loadedmetadata",cleanup,{once:true});
  sample.addEventListener("error",()=>{durationRequest.delete(f.name);sample.removeAttribute("src")},{once:true});
 }
 function trackHTML(f){
  const name=e(f.name),song=e(f.title||f.name),voice=f.voice_applied===true?(f.voice_check_status==="warning"?"⚠ Проверь вокал":"С голосом"):f.voice_check_status==="rejected"?"Без переноса":"";
  const icoHeart=ico("heart");
  return '<article class="track'+(state.playing===f.name?" selected":"")+'" data-track="'+name+'">'
   +'<div class="track-cover"><svg class="ico cover-placeholder"><use href="#i-music"/></svg><img alt="" loading="lazy" src="'+e(art(f))+'" onerror="this.style.display=\'none\'"><button type="button" class="cover-play" data-op="play" title="Воспроизвести" aria-label="Воспроизвести '+song+'">'+ico("play")+'</button></div>'
   +'<div class="track-body" role="button" tabindex="0" data-op="open"><strong>'+song+'</strong><div class="track-chips"><span class="track-chip">'+e(genre(f))+'</span>'+(voice?'<span class="track-chip '+(f.voice_applied&&f.voice_check_status!=="warning"?"voice-chip-good":"voice-chip-bad")+'">'+e(voice)+'</span>':"")+'</div></div>'
   +'<div class="track-meta"><span class="track-duration">'+(durCache.get(f.name)||"—:—")+'</span><small>'+e(shortDate(f))+'</small></div>'
   +'<button class="icon-btn track-like'+(fav(f.name)?" active":"")+'" data-op="like" type="button" title="Избранное" aria-label="Избранное">'+icoHeart+'</button>'
   +'<button class="icon-btn" data-op="copy" type="button" title="Скопировать описание трека" aria-label="Скопировать описание">'+ico("copy")+'</button>'
   +'<button class="icon-btn track-more" data-op="open" type="button" aria-label="Подробнее о треке">'+ico("more")+'</button></article>'
 }
 function sortTracks(input){
  const x=[...input];
  if(state.sort==="old")x.sort((a,b)=>Number(a.mtime||0)-Number(b.mtime||0));
  else if(state.sort==="title")x.sort((a,b)=>String(a.title||a.name).localeCompare(String(b.title||b.name),"ru"));
  else x.sort((a,b)=>Number(b.mtime||0)-Number(a.mtime||0));
  return x
 }
 const filtered=(q,liked)=>state.tracks.filter(f=>(!liked||fav(f.name))&&(!q||(String(f.name+" "+f.title+" "+f.style_preview).toLocaleLowerCase("ru").includes(q))));
 function renderList(target,rows,empty="Пока нет композиций"){
  const root=$(target);
  if(!rows.length){root.innerHTML='<div class="empty-list">'+e(empty)+'</div>';return}
  root.innerHTML=rows.map(trackHTML).join("");
  const observe=root.querySelectorAll(".track");
  let ix=0;for(const row of observe){if(ix++>13)break;const f=trackMap().get(row.dataset.track);if(f)fetchDuration(f)}
 }
 function renderRecent(){
  const query=$("recentSearch").value.toLocaleLowerCase("ru").trim();
  const x=filtered(query,state.recentFilter==="liked").sort((a,b)=>Number(b.mtime||0)-Number(a.mtime||0));
  renderList("recentList",x.slice(0,18),state.tracks.length?"Ничего не найдено":"Новые треки появятся здесь после генерации");
 }
 function renderLibrary(){
  const query=$("librarySearch").value.toLocaleLowerCase("ru").trim();
  const result=sortTracks(filtered(query,state.libraryFilter==="liked"));
  const viewCount=state.loadLimit;
  renderList("libraryList",result.slice(0,viewCount),state.tracks.length?"По этому запросу треков нет":"Твои композиции появятся здесь");
  $("libraryCount").textContent="Показано "+Math.min(result.length,viewCount)+" из "+result.length;
  const more=$("loadMore");more.hidden=result.length<=viewCount;more.textContent="Показать ещё · "+(result.length-viewCount);
 }
 function renderMelodyResults(){
  const m=state.job?.files?.filter(x=>x.name)?.slice(0,2)||[];
  renderList("melodyResultList",m.length?m.filter(x=>state.tracks.some(t=>t.name===x.name)).map(x=>state.tracks.find(t=>t.name===x.name)):[],"Здесь появятся новые аранжировки");
 }
 $("recentSearch").addEventListener("input",renderRecent);$("librarySearch").addEventListener("input",()=>{state.loadLimit=40;renderLibrary()});
 $("recentAll").addEventListener("click",()=>{state.recentFilter="all";$("recentAll").classList.add("active");$("recentLiked").classList.remove("active");renderRecent()});
 $("recentLiked").addEventListener("click",()=>{state.recentFilter="liked";$("recentLiked").classList.add("active");$("recentAll").classList.remove("active");renderRecent()});
 $("libraryAll").addEventListener("click",()=>{state.libraryFilter="all";$("libraryAll").classList.add("active");$("libraryLiked").classList.remove("active");renderLibrary()});
 $("libraryLiked").addEventListener("click",()=>{state.libraryFilter="liked";$("libraryLiked").classList.add("active");$("libraryAll").classList.remove("active");renderLibrary()});
 $("librarySort").addEventListener("change",ev=>{state.sort=ev.target.value;renderLibrary()});
 $("loadMore").addEventListener("click",()=>{state.loadLimit+=40;renderLibrary()});
 $("refreshLibrary").addEventListener("click",loadTracks);
 function playerUI(){
  const f=selectedFile(),playing=!audio.paused&&!!audio.src;
  $("playerTitle").textContent=f?.title||"Выбери песню";$("playerSubtitle").textContent=f?.when||"Music Studio";
  $("playerLike").classList.toggle("liked",!!(f&&fav(f.name)));
  $("playerLike").title=f&&fav(f.name)?"Убрать из избранного":"В избранное";
  const img=$("playerArt");img.hidden=!f;$("playerFallback").hidden=!!f;
  if(f && img.dataset.track!==f.name){img.dataset.track=f.name;img.src=art(f)}
  if(!f && img.dataset.track){delete img.dataset.track;img.removeAttribute("src")}
  const mainButton=$("playerPlay"), mainMode=playing?"pause":"play";
  if(mainButton.dataset.icon!==mainMode){mainButton.dataset.icon=mainMode;mainButton.innerHTML=ico(mainMode)}
  mainButton.classList.toggle("playing",playing);
  $("playerPlay").setAttribute("aria-label",playing?"Пауза":"Воспроизвести");
  $("currentTime").textContent=fmt(audio.currentTime);$("duration").textContent=fmt(audio.duration);
  if(!document.querySelector("#seek:active"))$("seek").value=Number.isFinite(audio.duration)&&audio.duration>0?Math.round(audio.currentTime/audio.duration*1000):0;
  document.querySelectorAll(".track").forEach(row=>{
   const yes=row.dataset.track===state.playing;row.classList.toggle("selected",yes);
   row.classList.toggle("playing",yes&&playing);
   const b=row.querySelector(".cover-play");
   if(b){const nextMode=(yes&&playing)?"pause":"play";
    if(b.dataset.icon!==nextMode){b.dataset.icon=nextMode;b.innerHTML=ico(nextMode)}
    b.setAttribute("aria-label",nextMode==="pause"?"Пауза":"Воспроизвести");}

  });
 }
 let playRevision=0,playPending=false;
 function play(f){
  if(!f)return;
  const changed=state.playing!==f.name||!audio.src;
  const pauseCurrent=!changed&&(!audio.paused||playPending);
  const revision=++playRevision;
  if(pauseCurrent){
   playPending=false;audio.pause();playerUI();return;
  }
  if(changed){
   // Always stop the previous source before loading the new one.
   audio.pause();playPending=false;
   state.playing=f.name;
   audio.src="/api/audio/"+encodeURIComponent(f.name);
   audio.load();
  }
  playPending=true;
  let request;
  try{request=audio.play()}catch(err){playPending=false;playerUI();toast("Не удалось запустить MP3: "+(err.message||err),"error");return}
  playerUI();
  if(request&&typeof request.then==="function"){
   request.then(()=>{
    if(revision!==playRevision)return;
    playPending=false;playerUI();
   }).catch(err=>{
    // A new song or user pause intentionally aborts the previous play promise.
    if(revision!==playRevision||err?.name==="AbortError")return;
    playPending=false;playerUI();
    toast("Не удалось воспроизвести MP3: "+(err?.message||"ошибка браузера"),"error");
   });
  }else{playPending=false}
 }
 function stepSong(dir){
  if(!state.tracks.length)return;
  let n=state.tracks.findIndex(f=>f.name===state.playing);
  n=state.shuffle?Math.floor(Math.random()*state.tracks.length):(n+dir+state.tracks.length)%state.tracks.length;
  const f=state.tracks[n];state.playing="";play(f)
 }
 ["play","pause","timeupdate","loadedmetadata","ended"].forEach(n=>audio.addEventListener(n,()=>{if(n==="ended"){if(state.repeat){audio.currentTime=0;audio.play().catch(()=>{})}else stepSong(1)}playerUI()}));
 $("playerPlay").addEventListener("click",()=>{const f=selectedFile()||state.tracks[0];if(f)play(f);else toast("Пока нет песен")});
 $("prevBtn").addEventListener("click",()=>stepSong(-1));$("nextBtn").addEventListener("click",()=>stepSong(1));
 $("seek").addEventListener("input",ev=>{if(audio.duration)audio.currentTime=Number(ev.target.value)*audio.duration/1000});
 $("volume").addEventListener("input",ev=>{audio.volume=Number(ev.target.value);audio.muted=false;store("studio50.volume",audio.volume)});
 $("shuffleBtn").addEventListener("click",()=>{state.shuffle=!state.shuffle;$("shuffleBtn").classList.toggle("active",state.shuffle)});
 $("repeatBtn").addEventListener("click",()=>{state.repeat=!state.repeat;$("repeatBtn").classList.toggle("active",state.repeat)});
 $("playerLike").addEventListener("click",()=>{if(state.playing)toggleFav(state.playing)});
 function toggleFav(name){
  if(state.fav[name])delete state.fav[name];else state.fav[name]=1;
  saveFavorites();renderRecent();renderLibrary();playerUI()
 }
 async function trackClicked(ev){
  const btn=ev.target.closest("[data-op]");if(!btn)return;
  const row=btn.closest("[data-track]");if(!row)return;
  const f=trackMap().get(row.dataset.track);if(!f)return;
  const action=btn.dataset.op;
  if(action==="play")play(f);
  if(action==="open")await openDrawer(f);
  if(action==="like")toggleFav(f.name);
  if(action==="copy")copy(String(f.style_preview||f.title||f.name));
 }
 ["recentList","libraryList","melodyResultList"].forEach(id=>{
  $(id).addEventListener("click",trackClicked);
  $(id).addEventListener("keydown",ev=>{if(ev.key==="Enter"&&ev.target.matches(".track-body")){ev.preventDefault();trackClicked(ev)}})
 });
 const drawer=$("trackDrawer");
 let drawerTicket=0;
 function closeDrawer(){
  drawer.classList.remove("open");drawer.setAttribute("aria-hidden","true");$("drawerBackdrop").hidden=true;state.inspected=null;
 }
 $("drawerClose").addEventListener("click",closeDrawer);$("drawerBackdrop").addEventListener("click",closeDrawer);
 document.addEventListener("keydown",ev=>{if(ev.key==="Escape"&&drawer.classList.contains("open"))closeDrawer()});
 function expand(id){const root=$(id);const is=root.classList.toggle("expanded");$("drawerExpand"+(id==="drawerStyle"?"Style":"Words")).textContent=is?"Свернуть":"Развернуть"}
 $("drawerExpandStyle").addEventListener("click",()=>expand("drawerStyle"));
 $("drawerExpandWords").addEventListener("click",()=>expand("drawerWords"));
 $("drawerCopyStyle").addEventListener("click",()=>copy($("drawerStyle").textContent));
 $("drawerCopyWords").addEventListener("click",()=>copy($("drawerWords").textContent));
 $("drawerPlay").addEventListener("click",()=>{if(state.inspected)play(state.inspected)});
 async function openDrawer(file){
  if(!file)return;
  const id=++drawerTicket;state.inspected=file;
  $("drawerBackdrop").hidden=false;drawer.classList.add("open");drawer.setAttribute("aria-hidden","false");
  $("drawerArt").src=art(file);$("drawerTitle").textContent=file.title||file.name;
  $("drawerMeta").textContent=(file.when||"")+" · "+genre(file);
  const suspiciousVoice=file.voice_check_status==="warning";
  $("drawerVoiceStatus").textContent=suspiciousVoice?"⚠ Качество голоса требует проверки: "+String(file.voice_check_note||"замечены провалы уровня").slice(0,180):file.voice_applied?"✓ Референс голоса использован (акустическое качество не подтверждено)":file.voice_check_status==="rejected"?"⚠ Голос не перенесён":"";
  $("drawerVoiceStatus").className="voice-tag "+(suspiciousVoice||file.voice_check_status==="rejected"?"warn":file.voice_applied?"good":"");
  $("drawerDownload").href="/api/audio/"+encodeURIComponent(file.name);$("drawerDownload").download=file.name;
  $("drawerStyle").textContent="Загружаем…";$("drawerWords").textContent="Загружаем…";
  $("drawerStyle").classList.remove("expanded");$("drawerWords").classList.remove("expanded");
  $("drawerExpandStyle").textContent="Развернуть";$("drawerExpandWords").textContent="Развернуть";
  const exports=$("drawerExports");exports.replaceChildren();
  for(const [url,title] of [[file.master_url,"WAV-мастер"],[file.original_url,"Исходная версия"]]){
   if(!url)continue;const a=document.createElement("a");a.textContent="↓ "+title;a.href=url;a.download="";exports.append(a);
  }
  try{const r=await json("/api/track_details?name="+encodeURIComponent(file.name));
   if(drawerTicket!==id||!state.inspected||state.inspected.name!==file.name)return;
   $("drawerStyle").textContent=r.style_original||r.model_caption||"Стиль не сохранён.";
   $("drawerWords").textContent=r.lyrics_original||r.lyrics_sent||"Текст не сохранён.";
  }catch(err){if(drawerTicket===id){$("drawerStyle").textContent="Не удалось загрузить: "+err.message;$("drawerWords").textContent="Нет сохранённого текста";}}
 }
 $("drawerDelete").addEventListener("click",async()=>{
  const f=state.inspected;if(!f)return;
  if(!confirm("Переместить «"+(f.title||f.name)+"» в корзину треков?"))return;
  try{
   const r=await post("/api/remove_track",{name:f.name});closeDrawer();
   if(state.playing===f.name){audio.pause();audio.removeAttribute("src");audio.load();state.playing=null;playerUI()}
   await loadTracks();
   toast("Трек перемещён в корзину","",async()=>{await post("/api/restore_track",{name:f.name,token:r.undo_token});await loadTracks();toast("Трек восстановлен")});
  }catch(err){toast(err.message,"error")}
 });
 // Voice previews read the real recordings; waveforms are derived from decoded audio.
 const voiceAudio=new Audio();let voicePlayer="",waveData=new Map(),waveContexts=new Map(),waveTimers=new Map();
 const voiceCtx=window.AudioContext||window.webkitAudioContext;
 const waveformPending=new Map();
 async function voiceAmps(file){
  if(waveData.has(file.name))return waveData.get(file.name);
  if(waveformPending.has(file.name))return waveformPending.get(file.name);
  const p=(async()=>{
   if(!voiceCtx)return[];
   const response=await fetch("/api/voice/"+encodeURIComponent(file.name));
   if(!response.ok)throw Error("Ошибка загрузки");
   const bytes=await response.arrayBuffer(),ctx=new voiceCtx();
   let decoded;try{decoded=await ctx.decodeAudioData(bytes)}finally{ctx.close().catch(()=>{})}
   const x=decoded.getChannelData(0),bins=120,amps=[];
   for(let i=0;i<bins;i++){
    const lo=Math.floor(i*x.length/bins),hi=Math.min(x.length,Math.floor((i+1)*x.length/bins)),step=Math.max(1,Math.floor((hi-lo)/80));
    let sum=0,n=0;for(let k=lo;k<hi;k+=step){sum+=x[k]*x[k];n++}
    amps.push(Math.sqrt(sum/Math.max(1,n)));
   }
   const max=Math.max(.00001,...amps);const scaled=amps.map(a=>clamp(Math.sqrt(a/max),.09,1));
   waveData.set(file.name,scaled);return scaled;
  })();
  waveformPending.set(file.name,p);
  try{return await p}finally{waveformPending.delete(file.name)}
 }
 function paintWave(canvas,amp,ratio,warning){
  if(!canvas)return;
  const bounds=canvas.getBoundingClientRect();if(bounds.width<10)return;
  const dpr=Math.min(2,window.devicePixelRatio||1);canvas.width=Math.round(bounds.width*dpr);canvas.height=Math.round(bounds.height*dpr);
  const ctx=canvas.getContext("2d");if(!ctx)return;ctx.clearRect(0,0,canvas.width,canvas.height);
  const samples=amp||Array(120).fill(.08),n=samples.length,gap=1.25*dpr,bw=(canvas.width-gap*(n-1))/n;
  for(let i=0;i<n;i++){const h=Math.max(2*dpr,samples[i]*canvas.height*.8),x=i*(bw+gap),y=(canvas.height-h)/2;ctx.fillStyle=i/n<ratio?(warning?"#ed8664":"#ffac5b"):"#697682";ctx.beginPath();ctx.roundRect?.(x,y,Math.max(1,bw),h,bw/2);ctx.fill();}
 }
 function renderVoices(){
  if(!$("voicesList"))return;
  const q=$("voiceSearch").value.toLocaleLowerCase("ru").trim();
  const items=state.voices.filter(f=>!q||f.name.toLocaleLowerCase("ru").includes(q));
  $("voiceTotal").textContent=items.length+" из "+state.voices.length;
  $("voicesList").innerHTML=items.length?items.map(f=>{
   const active=state.useVoice&&state.selectedVoice===f.name,warning=!!f.recording_warning,title=f.name.replace(/^\d{8}_\d{6}_/,"").replace(/_[a-f0-9]{6}\./i,".");
   return '<article class="voice-card'+(active?" active":"")+(warning?" overload":"")+'" data-voice="'+e(f.name)+'">'
    +'<div class="voice-card-head"><div class="voice-card-copy"><b class="voice-card-title" title="'+e(f.name)+'">'+e(active?"Мой голос (выбранная запись)":title)+'</b><small>'+e(f.when||"")+" · "+(Number(f.size||0)/1048576).toFixed(1)+' МБ</small></div>'+(active?'<span class="status-pill">✓ Используется</span>':warning?'<span class="status-pill warn">'+e(Number(f.recording_seconds)>0&&Number(f.recording_seconds)<15?"⚠ Короткая запись":"⚠ Проверить запись")+'</span>':"")+'</div>'
    +'<div class="voice-audio"><button class="voice-play" data-vop="play" type="button" aria-label="Воспроизвести запись">'+ico("play")+'</button><div class="voice-wave"><canvas width="420" height="42" data-vop="seek" role="slider" aria-label="Перемотка записи" tabindex="0" aria-valuemin="0" aria-valuenow="0" aria-valuemax="100"></canvas><div class="voice-times"><span class="vc-now">0:00</span><span class="vc-end">'+(f.recording_seconds?fmt(f.recording_seconds):"—:—")+'</span></div></div></div>'
    +'<div class="voice-actions"><button data-vop="use" class="voice-use">'+ico("music")+(active?" Выбрано":" Использовать в треке")+'</button><button data-vop="remove" class="icon-btn" type="button" title="Удалить запись" aria-label="Удалить запись">'+ico("trash")+'</button></div></article>'
  }).join(""):'<div class="empty-list">Голосовых записей нет. Создай первый профиль или загрузи файл.</div>';
  renderVoiceChipWithoutRecursion();
  for(const row of $("voicesList").querySelectorAll(".voice-card")){
   const f=state.voices.find(v=>v.name===row.dataset.voice);
   if(!f)continue;
   const canvas=row.querySelector("canvas");paintWave(canvas,waveData.get(f.name),voicePlayer===f.name&&voiceAudio.duration?voiceAudio.currentTime/voiceAudio.duration:0,!!f.recording_warning)
   if(!waveData.has(f.name))voiceAmps(f).then(a=>{if(canvas.isConnected)paintWave(canvas,a,voicePlayer===f.name&&voiceAudio.duration?voiceAudio.currentTime/voiceAudio.duration:0,!!f.recording_warning)}).catch(()=>{})
  }
 }
 function renderVoiceChipWithoutRecursion(){
  const active=state.useVoice&&!!state.selectedVoice;
  const meta=state.voices.find(x=>x.name===state.selectedVoice);
  $("voiceNotice").classList.toggle("has-voice",active);$("voiceNoticeTitle").textContent=active?(meta?.profile_id?"Мой голос · профиль":"⚠ Базовая голосовая модель"):(state.selectedVoice?"⚠ Перенос голоса выключен":"Голос не выбран");
  $("voiceNoticeDescription").textContent=active?(meta?.profile_id?"Запись связана с профилем; персональную модель определяет сервер.":"Запись не привязана к профилю; применяется базовая Seed-VC, тембр может не совпасть."):(state.selectedVoice?"Запись выбрана, но не будет использована. Включи Мой голос в параметрах.":"Выбери запись голоса, чтобы использовать свой тембр.");
 }
 $("voiceSearch").addEventListener("input",renderVoices);
 $("voicesList").addEventListener("click",async ev=>{
  const b=ev.target.closest("[data-vop]"),card=b?.closest("[data-voice]");if(!card)return;const name=card.dataset.voice;
  if(b.dataset.vop==="use"){state.selectedVoice=name;state.useVoice=true;renderVoiceChip();renderVoices();toast("Запись выбрана для генерации");return}
  if(b.dataset.vop==="remove"){
   if(!confirm("Удалить голосовую запись «"+name+"» с компьютера?"))return;
   try{await post("/api/remove_voice",{name});if(name===state.selectedVoice){state.selectedVoice="";state.useVoice=false}await loadVoices();toast("Запись удалена")}catch(ex){toast(ex.message,"error")}return;
  }
  if(b.dataset.vop==="play"){
   if(voicePlayer!==name){voicePlayer=name;voiceAudio.src="/api/voice/"+encodeURIComponent(name);voiceAudio.load()}
   if(voiceAudio.paused)voiceAudio.play().catch(()=>toast("Не удалось воспроизвести запись","error"));else voiceAudio.pause();
   return;
  }
  if(b.dataset.vop==="seek"&&voiceAudio.duration){
   if(voicePlayer!==name)return;
   const rect=b.getBoundingClientRect();voiceAudio.currentTime=clamp((ev.clientX-rect.left)/rect.width,0,1)*voiceAudio.duration
  }
 });
 $("voicesList").addEventListener("keydown",ev=>{if(!ev.target.matches("canvas"))return;if(!["ArrowLeft","ArrowRight"].includes(ev.key))return;ev.preventDefault();if(voiceAudio.duration)voiceAudio.currentTime=clamp(voiceAudio.currentTime+(ev.key==="ArrowRight"?2:-2),0,voiceAudio.duration)});
 function updateVoiceProgress(){
  for(const row of $("voicesList").querySelectorAll(".voice-card")){
   const on=row.dataset.voice===voicePlayer;row.querySelector(".vc-now").textContent=on?fmt(voiceAudio.currentTime):"0:00";
   const end=row.querySelector(".vc-end");if(on&&voiceAudio.duration)end.textContent=fmt(voiceAudio.duration);
   const c=row.querySelector("canvas");if(on)paintWave(c,waveData.get(voicePlayer),voiceAudio.duration?voiceAudio.currentTime/voiceAudio.duration:0,false);
   const play=row.querySelector(".voice-play");play.innerHTML=ico(on&&!voiceAudio.paused?"pause":"play");
  }
 }
 ["timeupdate","play","pause","loadedmetadata"].forEach(evt=>voiceAudio.addEventListener(evt,updateVoiceProgress));
 // Recording: PCM microphone, explicit user action only; browser fallback converts audio to WAV.
 let currentCapture=null,recordTick=null,recordStartAt=0,liveCtx=null,liveAnalyser=null,liveFrame=null;
 function liveMeter(canvas){
  if(!liveAnalyser||!canvas)return;
  const ctx=canvas.getContext("2d"),data=new Uint8Array(liveAnalyser.fftSize);
  liveAnalyser.getByteTimeDomainData(data);canvas.width=canvas.clientWidth*devicePixelRatio;canvas.height=104*devicePixelRatio;
  const w=canvas.width,h=canvas.height;ctx.clearRect(0,0,w,h);
  ctx.strokeStyle="#ffae65";ctx.lineWidth=1.7*devicePixelRatio;ctx.beginPath();
  for(let i=0;i<data.length;i++){const x=i/(data.length-1)*w,y=(data[i]-128)/128*h*.41+h*.5;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)}ctx.stroke();
  liveFrame=requestAnimationFrame(()=>liveMeter(canvas));
 }
 async function encodeWavFromBrowser(blob){
  if(blob.type==="audio/wav"||blob.type==="audio/x-wav")return blob;
  const ctor=window.AudioContext||window.webkitAudioContext,ctx=new ctor();
  try{
   const buffer=await ctx.decodeAudioData(await blob.arrayBuffer());
   const channels=buffer.numberOfChannels,n=buffer.length,sum=new Float32Array(n);
   for(let c=0;c<channels;c++){const samples=buffer.getChannelData(c);for(let i=0;i<n;i++)sum[i]+=samples[i]/channels}
   if(window.StudioLosslessRecorder)return window.StudioLosslessRecorder.encodeWAV([sum],buffer.sampleRate);
   const out=new ArrayBuffer(44+n*2),v=new DataView(out),w=(at,s)=>{for(let i=0;i<s.length;i++)v.setUint8(at+i,s.charCodeAt(i))};
   w(0,"RIFF");v.setUint32(4,36+n*2,true);w(8,"WAVE");w(12,"fmt ");v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,buffer.sampleRate,true);v.setUint32(28,buffer.sampleRate*2,true);v.setUint16(32,2,true);v.setUint16(34,16,true);w(36,"data");v.setUint32(40,n*2,true);
   for(let i=0;i<n;i++)v.setInt16(44+i*2,Math.round(clamp(sum[i],-1,1)*32767),true);
   return new Blob([out],{type:"audio/wav"});
  }finally{ctx.close().catch(()=>{})}
 }
 function releaseCapture(){
  if(recordTick){clearInterval(recordTick);recordTick=null}
  if(liveFrame){cancelAnimationFrame(liveFrame);liveFrame=null}
  if(liveCtx){liveCtx.close().catch(()=>{});liveCtx=null;liveAnalyser=null}
  if(currentCapture){currentCapture.stream.getTracks().forEach(x=>x.stop());currentCapture=null}
  $("melodyStop").disabled=true;$("voiceRecStop").disabled=true;
 }
 async function startCapture(target){
  if(currentCapture)return toast("Микрофон уже используется","error");
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw Error("Доступ к микрофону возможен на localhost или HTTPS");
   const stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
   const rec=window.StudioLosslessRecorder?new window.StudioLosslessRecorder(stream):new MediaRecorder(stream);
   const c={stream,rec,target,parts:[],mime:rec.mimeType||"audio/webm",stopping:false};currentCapture=c;
   rec.addEventListener("dataavailable",ev=>{if(ev.data?.size)c.parts.push(ev.data)});
   rec.addEventListener("error",ev=>{toast("Ошибка микрофона: "+(ev.error?.message||"проверь устройство"),"error");releaseCapture()});
   rec.addEventListener("stop",async()=>{
    if(currentCapture!==c)return;
    releaseCapture();
    $("melodyRecordingState").classList.remove("recording");
    $("melodyRecordingState").querySelector("span:nth-child(2)").textContent="Запись завершена";
    $("voiceRecState").textContent="Запись завершена";
    try{
     let blob=new Blob(c.parts,{type:c.mime});
     if(!c.parts.length)throw Error("Не удалось записать аудио");
     blob=await encodeWavFromBrowser(blob);
     if(blob.size>88*1024*1024)throw Error("Файл слишком большой");
     const name=(target==="melody"?"Моя мелодия":"Мой голос")+" "+Date.now()+".wav";
     const file=new File([blob],name,{type:"audio/wav"});
     if(target==="melody"){state.melody.recorded=true;await loadMelodyFile(file)}
     else setVoiceDraft(file);
    }catch(err){toast("Запись: "+err.message,"error")}
   });
   rec.start();recordStartAt=performance.now();
   if(target==="melody"){$("melodyStart").disabled=true;$("melodyStop").disabled=false;$("melodyRecordingState").classList.add("recording");$("melodyRecordingState").querySelector("span:nth-child(2)").textContent="Идёт запись"}
   else{$("voiceRecStart").disabled=true;$("voiceRecStop").disabled=false;$("voiceRecState").textContent="● Идёт запись"}
   recordTick=setInterval(()=>{
    const t=Math.round((performance.now()-recordStartAt)/1000);
    if(target==="melody")$("melodyRecordTimer").textContent=fmt(t);
    else $("voiceRecClock").textContent=fmt(t);
    if(t>=125)stopCapture();
   },260);
   try{
    liveCtx=new(window.AudioContext||window.webkitAudioContext)();liveAnalyser=liveCtx.createAnalyser();liveAnalyser.fftSize=1024;
    const source=liveCtx.createMediaStreamSource(stream);source.connect(liveAnalyser);
    if(target==="melody")liveMeter($("melodyLiveWave"));
   }catch{}
  }catch(err){toast("Микрофон: "+err.message,"error");releaseCapture()}
 }
 function stopCapture(){
  if(currentCapture&&!currentCapture.stopping){currentCapture.stopping=true;currentCapture.rec.stop()}
 }
 $("melodyStart").addEventListener("click",()=>startCapture("melody"));
 $("melodyStop").addEventListener("click",stopCapture);
 $("voiceRecStart").addEventListener("click",()=>startCapture("voice"));
 $("voiceRecStop").addEventListener("click",stopCapture);
 document.addEventListener("visibilitychange",()=>{/* Recording continues in background tab; user must stop explicitly. */});
 window.addEventListener("pagehide",()=>{if(currentCapture)stopCapture();releaseCapture();if(state.melody.url)URL.revokeObjectURL(state.melody.url)});
 // Melody studio: genuine upload + source-audio conditioning. Never pretend model retained exact notes.
 function setMelodyKind(kind){
  state.melody.kind=kind;
  document.querySelectorAll("[data-idea]").forEach(b=>b.classList.toggle("selected",b.dataset.idea===kind));
  // A sung sketch is not a speaker profile: only an explicitly selected voice is eligible.
  $("melodyUseVoice").checked=kind==="vocal" && state.useVoice && !!state.selectedVoice;
  refreshMelodyVoiceLabel();
  $("melodyStatus").textContent=kind==="hum"?"Напой мотив. Исходник будет использован при создании аранжировки.":kind==="vocal"?"Спой или прочитай фразу — можно использовать её как источник тембра.":"Загрузи WAV, MP3 или M4A. Исходник останется без изменений.";
 }
 document.querySelectorAll("[data-idea]").forEach(b=>b.addEventListener("click",()=>setMelodyKind(b.dataset.idea)));
 function refreshMelodyVoiceLabel(){
  const node=$("melodyVoiceSelection"); if(!node)return;
  node.textContent=state.selectedVoice ? "Профиль голоса: "+state.selectedVoice : "Выбери отдельную запись голоса. Напев не заменяет голосовой профиль.";
 }
 $("melodyChooseVoice").addEventListener("click",()=>openParams("voice"));
 $("melodyFile").addEventListener("change",async ev=>{const f=ev.target.files?.[0];if(f)await loadMelodyFile(f)});
 $("melodyReset").addEventListener("click",()=>{
  if(state.melody.url)URL.revokeObjectURL(state.melody.url);
  state.melody={kind:"hum",file:null,blob:null,url:"",source:"",voiceFile:"",duration:0,notes:[],recorded:false,usingMic:false};
  $("melodyPreview").hidden=true;$("melodyFile").value="";
  $("melodyRecordTimer").textContent="0:00";$("melodyRecordingState").querySelector("span:nth-child(2)").textContent="Готов к записи";
  $("melodyStatus").textContent="Запиши или загрузи аудио";setMelodyKind("hum");renderMelody()
 });
 async function loadMelodyFile(file){
  if(state.melody.url)URL.revokeObjectURL(state.melody.url);
  state.melody.file=file;state.melody.url=URL.createObjectURL(file);state.melody.source="";state.melody.voiceFile="";
  $("melodyPreviewAudio").src=state.melody.url;$("melodyPreview").hidden=false;
  $("melodyPreviewAudio").onloadedmetadata=()=>{$("melodyClipLength").textContent=fmt($("melodyPreviewAudio").duration);state.melody.duration=$("melodyPreviewAudio").duration};
  $("melodyPitchInfo").textContent="Анализируем ноты реального аудио…";
  $("melodyStatus").textContent="Аудиодорожка готова: "+file.name;
  renderMelody();analyzeMelody(file).catch(err=>{$("melodyPitchInfo").textContent="Анализ нот недоступен: "+err.message});
 }
 function renderMelody(){
  $("melodyGenerate").disabled=!state.melody.file||["preparing","generating","converting"].includes(state.job?.status);
  $("melodyStep1").classList.toggle("active",!state.melody.file);
  $("melodyStep2").classList.toggle("active",!!state.melody.file);
  $("melodyStep3").classList.toggle("active",["preparing","generating","converting"].includes(state.job?.status));
  $("melodyStart").disabled=!!currentCapture;
 }
 // A lightweight offline monophonic pitch tracker; results are visual guidance, not a vocal transcription.
 async function analyzeMelody(file){
  const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;
  const ctx=new AC();
  let decoded;try{decoded=await ctx.decodeAudioData(await file.arrayBuffer())}finally{ctx.close().catch(()=>{})}
  if(!state.melody.file||state.melody.file!==file)return;
  const channel=decoded.getChannelData(0),sr=decoded.sampleRate,secs=Math.min(decoded.duration,95);
  const rate=11025,rateScale=sr/rate,stepSeconds=.105,hop=Math.max(1,Math.floor(rate*stepSeconds)),windowSize=660;
  const notes=[],total=Math.min(650,Math.floor(secs/stepSeconds));
  for(let t=0;t<total;t++){
   const start=t*hop;let rms=0,buf=new Float32Array(windowSize);
   for(let i=0;i<windowSize;i++){
    const ix=Math.floor((start+i)*rateScale);
    const v=channel[ix]||0;buf[i]=v;rms+=v*v;
   }
   rms=Math.sqrt(rms/windowSize);
   if(rms<.008){notes.push(null);continue}
   let bestLag=0,best=Infinity;
   // AMDF over plausible sung voice range (around 90-850 Hz).
   for(let lag=13;lag<=122;lag++){
    let diff=0,energy=0;for(let j=0;j<windowSize-lag;j+=3){const d=buf[j]-buf[j+lag];diff+=d*d;energy+=buf[j]*buf[j]+buf[j+lag]*buf[j+lag]}
    const score=diff/(energy+1e-6);
    if(score<best){best=score;bestLag=lag}
   }
   if(best>.34||!bestLag)notes.push(null);
   else{
    const frequency=rate/bestLag,midi=69+12*Math.log2(frequency/440);
    notes.push(clamp(Math.round(midi),36,90));
   }
  }
  if(state.melody.file!==file)return;
  // Collapse consecutive frames into notes; single-frame clicks are suppressed.
  const segments=[];let start=-1,last=null;
  for(let i=0;i<=notes.length;i++){
   const key=notes[i]??null;
   if(key!==last){
    if(last!==null&&i-start>=2)segments.push({n:last,at:start*stepSeconds,dt:(i-start)*stepSeconds});
    start=i;last=key;
   }
  }
  state.melody.notes=segments;
  drawPitch(segments,Math.max(2,secs));
  $("melodyPitchInfo").textContent=segments.length
   ?("Найдено около "+segments.length+" нот. Это приблизительный контур — финальный звук зависит от музыкальной модели.")
   :"Не удалось уверенно распознать отдельные ноты. Аудио всё равно можно использовать как референс.";
 }
 function drawPitch(segments,duration){
  const c=$("melodyPitch"),r=c.getBoundingClientRect(),dpr=Math.min(2,window.devicePixelRatio||1);
  const w=Math.max(500,Math.round(r.width*dpr)),h=Math.round(118*dpr);
  c.width=w;c.height=h;const ctx=c.getContext("2d");ctx.clearRect(0,0,w,h);
  ctx.fillStyle="#101821";ctx.fillRect(0,0,w,h);
  for(let i=0;i<12;i++){ctx.strokeStyle=i%3===0?"#364450":"#26323b";ctx.beginPath();const y=i/12*h;ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
  for(let i=0;i<12;i++){ctx.strokeStyle="#26313a";ctx.beginPath();const x=i/12*w;ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}
  for(const note of segments){
   const x=note.at/duration*w,barW=Math.max(3,note.dt/duration*w),y=h-(note.n-36)/(90-36)*h;
   ctx.fillStyle="#ffad5c";ctx.fillRect(x,clamp(y-4*dpr,2,h-9*dpr),barW,8*dpr);
  }
 }
 function updateMelodyButton(){renderMelody()}
 $("melodyGenerate").addEventListener("click",async()=>{
  if(!state.melody.file)return toast("Сначала запиши мелодию","error");
  const style=$("melodyStyle").value.trim(),lyrics=$("melodyWords").value.trim();
  if(!style)return toast("Опиши стиль будущего трека","error");
  const btn=$("melodyGenerate");btn.disabled=true;
  try{
   let source=state.melody.source;
   if(!source){$("melodyStatus").textContent="Сохраняем исходную дорожку…";const r=await upload(state.melody.file,"remix");source=r.name;state.melody.source=source}
   // Explicit per-arrangement voice opt-in. Preserve the globally selected profile.
   const useVoice=$("melodyUseVoice").checked;
   const voice=useVoice?state.selectedVoice:"";
   if(useVoice&&!voice){toast("Сначала выбери отдельную голосовую запись.","error");openParams("voice");return}
   // The melodic sketch is NEVER uploaded as a voice reference or silently selected.
   const data={title:$("melodyName").value.trim(),style,lyrics,bpm:Number($("melodyBpm").value)||0,
    duration:Number($("melodyDuration").value)||0,instrumental:!lyrics,
    vocal_language:"auto",vocal_gender:"auto",mode:"remix",source,quality:"composer",
    use_voice:useVoice,voice,voice_profile_id:state.voices.find(v=>v.name===voice)?.profile_id||"",
    use_trained_groove_reference:false,
    apply_voice:true,trained_voice:false,voice_register:"auto",russian_rap:false,
    planner:true,producer:true,two_versions:state.twoVersions};
   const ok=await generateTrack(data,"melody");if(ok){$("melodyStatus").textContent="Генерируем новую аранжировку на основе твоего аудио";}
  }catch(err){toast(err.message,"error")}finally{updateMelodyButton()}
 });
 // Own-voice wizard: choose language, record or upload, confirm ownership, save locally.
 const samples={
  ru:{sing:["Свет над рекой и вечерний покой,\nЯ возвращаюсь с музыкой домой.\nТихий ветер, тёплый май,\nТы меня не забывай.",
   "В небе звёзды, а под ними сад,\nЯ вернусь, когда часы пробьют закат.\nПусть мой голос вдаль летит,\nИ душа опять поёт, звучит.",
   "Над волнами тихо тает свет,\nИ в душе рождается ответ.\nНочь нас снова позвала,\nСердце песню сберегло."],
   read:["Я записываю свой голос для музыкальной студии. Говорю спокойно, без напряжения. Эта запись поможет определить мои особенности произношения и тембр.",
    "Сегодня хорошая погода, и у меня много творческих идей. Я хочу, чтобы голос звучал естественно, мягко и без резких скачков высоты."]},
  en:{sing:["Over the water, under the sky,\nI hear the melody passing by.\nThe stars are shining, soft and bright,\nWe'll make a song of this summer night."],
   read:["I am recording my own voice for Music Studio. I am speaking naturally and clearly, at a comfortable volume. This recording is my voice reference."]}
 };
 let voiceSampleIndex=-1;
 function pickVoiceSample(){
  const lang=$("voiceLang").value,kind=$("voiceKind").value,x=samples[lang][kind];
  voiceSampleIndex=(voiceSampleIndex+1)%x.length;$("voiceSample").textContent=x[voiceSampleIndex]
 }
 $("anotherText").addEventListener("click",pickVoiceSample);
 $("voiceLang").addEventListener("change",()=>{voiceSampleIndex=-1;pickVoiceSample()});
 $("voiceKind").addEventListener("change",()=>{voiceSampleIndex=-1;pickVoiceSample()});
 function voiceWizardPage(){
  const n=state.modalStep;
  for(let i=1;i<=3;i++)$("voiceStep"+i).hidden=i!==n;
  [...document.querySelectorAll(".wizard-progress span")].forEach((el,i)=>el.classList.toggle("on",i<n));
  $("voiceBack").disabled=n===1;
  $("voiceNext").innerHTML=n===3?"Сохранить профиль "+ico("check"):"Продолжить "+ico("arrow");
  $("voiceWizardStatus").textContent=n+"/3";
 }
 function openVoiceWizard(){
  state.modalStep=1;$("voiceOwn").checked=false;
  if(state.voiceDraft.url)URL.revokeObjectURL(state.voiceDraft.url);
  state.voiceDraft={blob:null,name:"",url:""};$("voiceRecPreview").hidden=true;$("voiceFileStatus").textContent="";
  voiceSampleIndex=-1;pickVoiceSample();voiceWizardPage();openDialog("voiceDialog")
 }
 $("addVoice").addEventListener("click",openVoiceWizard);
 function setVoiceDraft(file){
  if(state.voiceDraft.url)URL.revokeObjectURL(state.voiceDraft.url);
  state.voiceDraft={blob:file,name:file.name,url:URL.createObjectURL(file)};
  $("voiceRecPreview").src=state.voiceDraft.url;$("voiceRecPreview").hidden=false;
  $("voiceFileStatus").textContent="Выбран файл: "+file.name+" · "+(file.size/1048576).toFixed(1)+" МБ";
  $("voiceRecStart").disabled=false;
  if(file.size>88*1048576)toast("Файл слишком большой","error")
 }
 $("voiceUpload").addEventListener("change",ev=>{const f=ev.target.files?.[0];if(f)setVoiceDraft(f)});
 $("voiceBack").addEventListener("click",()=>{if(state.modalStep>1){state.modalStep--;voiceWizardPage()}});
 $("voiceNext").addEventListener("click",async()=>{
  if(state.modalStep===1){state.modalStep=2;voiceWizardPage();return}
  if(state.modalStep===2){
   if(!state.voiceDraft.blob)return toast("Сначала запиши голос или выбери файл","error");
   state.modalStep=3;voiceWizardPage();return;
  }
  if(!$("voiceOwn").checked)return toast("Подтверди, что запись принадлежит тебе","error");
  const b=state.voiceDraft.blob;if(!b)return toast("Нет файла для сохранения","error");
  $("voiceNext").disabled=true;$("voiceWizardStatus").textContent="Сохраняем…";
  try{
   // QA76 stages are named explicitly so the later trainer can exclude
   // the withheld holdout by filename, never by guesswork or chronology.
   const training=window.studioTraining76Active;
   let submitted=b;
   if(training && /^[a-z_]{4,25}$/.test(training.id)){
    const ext=/\.(wav|mp3|flac|ogg|m4a|aac)$/i.exec(String(b.name||""))?.[1]?.toLowerCase()||"wav";
    const name="QA76_"+(training.heldout?"HOLDOUT_":"")+training.id+"_"+Date.now()+"."+ext;
    submitted=new File([b],name,{type:b.type||"application/octet-stream"});
   }
   const result=await upload(submitted,"voice");
   if(window.studioProfiles34?.bindUploadedVoice){
    try{await window.studioProfiles34.bindUploadedVoice(result.name)}
    catch(ex){toast("Запись сохранена, но профиль не назначен: "+ex.message,"error")}
   }
   if(!training){state.selectedVoice=result.name;state.useVoice=true;}
   await loadVoices();
   store("studio50.vocalLevel",document.querySelector('input[name="vocalLevel"]:checked')?.value||"new");
   if(training)document.dispatchEvent(new CustomEvent("studioTraining76:saved",{detail:{id:training.id,filename:result.name,heldout:!!training.heldout}}));
   closeDialog("voiceDialog");toast(training?"Обучающий дубль сохранён. Рабочий голос не переключался.":"Голосовой профиль сохранён и выбран для песни");view("voices");
  }catch(err){toast(err.message,"error")}finally{$("voiceNext").disabled=false;voiceWizardPage()}
 });
 $("voiceDialog").addEventListener("close",()=>{if(currentCapture?.target==="voice")stopCapture();window.studioTraining76Active=null});
 // Lyrics: exactly two editable variants. No random replacements to current song.
 $("writeLyrics").addEventListener("click",()=>{
  $("lyricsMood").value=$("songStyle").value;
  $("lyricsMessage").textContent="Опиши тему, затем выбери один из двух вариантов.";
  openDialog("lyricsDialog");$("lyricsTopic").focus()
 });
 let lyricsTask=null,lastLyricSig="",lyricsEditing=new Map();
 $("generateLyrics").addEventListener("click",async()=>{
  const topic=$("lyricsTopic").value.trim(),style=$("lyricsMood").value.trim()||$("songStyle").value.trim();
  if(!topic)return toast("Напиши тему будущей песни","error");
  if(!style)return toast("Укажи музыкальный стиль","error");
  $("generateLyrics").disabled=true;
  $("lyricsVariants").innerHTML="";
  try{
   const r=await post("/api/lyrics",{topic,style,vocal_language:"auto",vocal_gender:"auto"});
   lyricsTask=r.id;lastLyricSig="";
   $("lyricsMessage").textContent="Создаём ровно два варианта. Текст в редакторе не изменится до твоего выбора.";
   await pollLyrics();
  }catch(err){toast(err.message,"error");$("lyricsMessage").textContent=err.message;$("generateLyrics").disabled=false}
 });
 async function pollLyrics(){
  if(!lyricsTask)return;
  try{
   const r=await json("/api/lyrics");
   const busy=["preparing","generating"].includes(r.status);
   $("generateLyrics").disabled=busy;
   $("lyricsMessage").textContent=r.status==="error"?(r.error||"Ошибка текста"):(r.message||"");
   const list=(r.variants||[]).slice(0,2);
   const sig=JSON.stringify(list.map(x=>[x.id,x.lyrics]));
   if(list.length&&sig!==lastLyricSig){
    lastLyricSig=sig;lyricsEditing=new Map();$("lyricsVariants").replaceChildren();
    list.forEach((item,i)=>{
     const card=document.createElement("section");card.className="variant";
     const h=document.createElement("h3");h.textContent="Вариант "+(i+1);
     const textarea=document.createElement("textarea");textarea.value=item.lyrics||"";textarea.spellcheck=true;
     textarea.setAttribute("aria-label","Редактировать текст, вариант "+(i+1));
     const btn=document.createElement("button");btn.className="primary";btn.type="button";
     btn.innerHTML=ico("check")+" Выбрать вариант";
     btn.addEventListener("click",()=>{
      if($("songWords").value.trim()&&!confirm("Заменить текущий текст выбранным вариантом?"))return;
      $("songWords").value=textarea.value;
      if(!$("songStyle").value.trim())$("songStyle").value=$("lyricsMood").value.trim();
      persistComposer();updateCount();closeDialog("lyricsDialog");toast("Вариант "+(i+1)+" выбран");
     });
     card.append(h,textarea,btn);$("lyricsVariants").append(card);
    });
   }
   if(!busy){lyricsTask=null;$("generateLyrics").disabled=false}
  }catch(err){$("lyricsMessage").textContent=err.message}
 }
 // Settings: paths returned from server, no hardcoded user-folder paths.
 const storageTitles={tracks:"Готовые песни",covers:"Обложки",voices:"Мои записи",trash:"Корзина",exports:"Экспорт",originals:"Исходные версии",masters:"WAV-мастера"};
 async function loadSettings(){
  try{
   const data=await json("/api/settings/storage");
   const paths=data.paths||{},rows=$("storageRows");rows.replaceChildren();
   for(const [key,title] of Object.entries(storageTitles)){
    if(!paths[key])continue;
    const el=document.createElement("div");el.className="setting-row";
    const name=document.createElement("span");name.textContent=title;
    const btn=document.createElement("button");btn.type="button";btn.textContent="Открыть папку";btn.dataset.folder=key;btn.title=paths[key];
    el.append(name,btn);rows.append(el);
   }
  }catch(err){$("storageRows").textContent="Не удалось загрузить папки: "+err.message}
 }
 async function openFolder(kind){
  try{const r=await post("/api/open-folder",{kind});toast("Открыта папка в Проводнике Windows")}
  catch(ex){toast(ex.message,"error")}
 }
 $("storageRows").addEventListener("click",ev=>{const b=ev.target.closest("[data-folder]");if(b)openFolder(b.dataset.folder)});
 $("openTracksFolder").addEventListener("click",()=>openFolder("tracks"));
 $("openLogs").addEventListener("click",async()=>{
  const box=$("logs");
  if(!box.hidden){box.hidden=true;return}
  try{const r=await json("/api/log");box.textContent=r.text||"Журнал пуст.";box.hidden=false}
  catch(err){toast(err.message,"error")}
 });
 // Startup: do not reset song text, recordings or previously saved favorites.
 async function boot(){
  renderVoiceChip();renderVoices();renderRecent();renderLibrary();setInstrumental(false);
  $("createButton").innerHTML=ico("spark")+" Создать "+(state.twoVersions?"2 варианта":"1 вариант");
  $("melodyUseVoice").checked=false;setMelodyKind("hum");
  await Promise.all([loadTracks(),loadVoices(),checkHealth()]);
  statusPoll=setInterval(checkHealth,6500);
  lyricsPoll=setInterval(pollLyrics,2200);
 }
 window.addEventListener("error",err=>{if(err.message&&!err.message.includes("ResizeObserver"))toast("Ошибка интерфейса: "+err.message,"error")});
 boot().catch(ex=>toast("Не удалось запустить интерфейс: "+ex.message,"error"));
})();
