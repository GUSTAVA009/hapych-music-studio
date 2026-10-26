"use strict";
// One music engine; two selectable lyric drafts; microphone is user-initiated only.
(() => {
  let lyricSignature = "", chosenId = "", lyricRequest = false;
  const editedVariants = new Map();
  const fieldIds = ["songTopic","style","lyrics","title","duration","bpm","vocalLanguage","vocalGender"];
  const draftKey = "music-studio-unified15-draft";
  function saveDraft() {
    try {
      const draft = Object.fromEntries(fieldIds.map(id => [id,$(id).value]));
      draft.voice = selectedVoice; draft.useVoice = $("useVoice").checked; draft.chosenId = chosenId;
      localStorage.setItem(draftKey, JSON.stringify(draft));
    } catch (_) { /* Browser private mode may reject persistent storage. */ }
  }
  try {
    const draft = JSON.parse(localStorage.getItem(draftKey) || "null");
    if (draft && typeof draft === "object") {
      fieldIds.forEach(id => { if (typeof draft[id] === "string") $(id).value = draft[id]; });
      $("vocalLanguage").value="auto";$("vocalGender").value="auto";
      selectedVoice = typeof draft.voice === "string" ? draft.voice : "";
      $("useVoice").checked = Boolean(draft.useVoice);
      $("voiceChooser").classList.toggle("hidden",!$("useVoice").checked);
      chosenId = draft.chosenId || ""; reviewWords(); queuePreparation();
      if (selectedVoice) refreshVoices();
    }
  } catch (_) { /* An invalid saved draft must not break the studio. */ }
  fieldIds.forEach(id => $(id).addEventListener("input",saveDraft));
  $("voiceSelect").addEventListener("change",saveDraft);
  $("useVoice").addEventListener("change",saveDraft);
  $("lyrics").addEventListener("input", () => {
    $("chosenLyricLabel").textContent = "Текст можно редактировать. Генерация новой пары не заменит его без твоего выбора.";
  });
  function renderLyrics(job) {
    const busy = ["preparing","generating"].includes(job.status);
    window.studioLyricsBusy = busy;
    $("generateLyrics").disabled = busy || lyricRequest;
    $("regenerateLyrics").disabled = busy || lyricRequest || !(job.variants || []).length;
    $("lyricJobState").textContent = job.status === "error" ? job.error : job.message;
    const variants = (job.variants || []).slice(0,2);
    const signature = JSON.stringify(variants);
    if (signature !== lyricSignature) {
      lyricSignature = signature;
      const container = $("lyricVariants"); container.replaceChildren();
      variants.forEach((item,index) => {
        const card = element("article","lyric-candidate" + (chosenId === item.id ? " selected" : ""));
        card.dataset.variant = item.id;
        const title = element("h3","","Вариант " + (index+1));
        const text = element("textarea","lyric-preview");
        text.value=editedVariants.get(item.id) || item.lyrics; text.spellcheck=true;
        text.addEventListener("input",()=>editedVariants.set(item.id,text.value));
        text.tabIndex=0; text.setAttribute("aria-label","Текст варианта " + (index+1));
        const choose = element("button","secondary-button","Выбрать этот текст");
        choose.type = "button"; choose.dataset.choose = item.id;
        choose.addEventListener("click", () => {
          if ($("lyrics").value.trim() && chosenId !== item.id && !confirm("Заменить текущий текст выбранным вариантом?")) return;
          chosenId = item.id; $("lyrics").value = text.value;
          $("lyricDialog").close();
          $("style").value=$("lyricStyle").value.trim() || item.style || $("style").value;
          document.querySelectorAll(".lyric-candidate").forEach(c=>c.classList.toggle("selected",c.dataset.variant===chosenId));
          $("chosenLyricLabel").textContent = "Выбран вариант " + (index+1) + ". Отредактируй слова или переходи к созданию песни.";
          reviewWords(); queuePreparation(); saveDraft();
          notify("Выбран вариант " + (index+1));
        });
        card.append(title,text,choose);container.append(card);
      });
    }
    document.querySelectorAll("[data-choose]").forEach(button => button.disabled=busy);
  }
  async function refreshLyricJob() {
    try { renderLyrics(await call("/api/lyrics")); }
    catch (_) { /* The existing health badge reports a disconnected local server. */ }
  }
  async function generateLyricPair() {
    if (lyricRequest) return;
    const topic=$("songTopic").value.trim(),style=$("lyricStyle").value.trim() || $("style").value.trim();
    if (!topic) { $("songTopic").focus();$("lyricJobState").textContent="Напиши тему песни.";return; }
    if (!style) { $("lyricStyle").focus();$("lyricJobState").textContent="Опиши музыкальный стиль.";return; }
    saveDraft(); lyricRequest=true;
    $("generateLyrics").disabled=true;$("regenerateLyrics").disabled=true;
    try {
      await call("/api/lyrics",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({topic,style,
        vocal_language:"auto",vocal_gender:"auto"})});
      window.studioLyricsBusy=true;
      $("lyricJobState").textContent="Создаём ровно два варианта. Выбранный текст пока остаётся без изменений.";
      await refreshLyricJob();
    } catch(e) { notify(e.message,true);$("lyricJobState").textContent=e.message; }
    finally { lyricRequest=false; await refreshLyricJob(); }
  }
  $("openLyricDialog").addEventListener("click",()=>{
    if (!$("lyricStyle").value.trim()) $("lyricStyle").value=$("style").value;
    $("lyricDialog").showModal();$("songTopic").focus();
  });
  $("closeLyricDialog").addEventListener("click",()=>$("lyricDialog").close());
  $("lyricDialog").addEventListener("click",e=>{if(e.target===$("lyricDialog")){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $("generateLyrics").addEventListener("click",generateLyricPair);
  $("regenerateLyrics").addEventListener("click",generateLyricPair);
  refreshLyricJob();setInterval(refreshLyricJob,3500);

  let recorder=null,stream=null,chunks=[],recordedBlob=null,previewUrl=null;
  let audioContext=null,analyser=null,meterFrame=null,ticker=null,began=0,bytes=0;
  const recordingStatus = message => { $("recordStatus").textContent=message; };
  function releaseMicrophone() {
    if (ticker) clearInterval(ticker);ticker=null;
    if (meterFrame) cancelAnimationFrame(meterFrame);meterFrame=null;
    if (stream) stream.getTracks().forEach(track=>track.stop());stream=null;
    if (audioContext) audioContext.close().catch(()=>{});audioContext=null;analyser=null;
    $("recordLevel").value=0;
  }
  function stopRecording() {
    if (recorder && recorder.state !== "inactive") recorder.stop();
    else releaseMicrophone();
  }
  function showLevel() {
    if (!analyser) return;
    const buffer = new Uint8Array(analyser.fftSize);analyser.getByteTimeDomainData(buffer);
    const rms = Math.sqrt(buffer.reduce((sum,v)=>sum+((v-128)/128)**2,0)/buffer.length);
    $("recordLevel").value = Math.min(1,rms*4);
    meterFrame=requestAnimationFrame(showLevel);
  }
  async function startRecording() {
    if (stream || (recorder && recorder.state!=="inactive")) return;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || (!window.StudioLosslessRecorder && !window.MediaRecorder)) {
      return notify("Запись недоступна. Открой студию на localhost или по HTTPS; загрузка файла остаётся доступной.",true);
    }
    $("recordStart").disabled=true;$("recordAgain").disabled=true;
    recordingStatus("Запрашиваем разрешение на микрофон...");
    try {
      stream=await navigator.mediaDevices.getUserMedia({audio:{channelCount:1,echoCancellation:false,noiseSuppression:false,autoGainControl:false},video:false});
      const type=window.MediaRecorder ? ["audio/webm;codecs=opus","audio/ogg;codecs=opus","audio/mp4"].find(t=>MediaRecorder.isTypeSupported(t)) : null;
      recorder=window.StudioLosslessRecorder
        ? new window.StudioLosslessRecorder(stream)
        : new MediaRecorder(stream,type?{mimeType:type,audioBitsPerSecond:192000}:undefined);
      chunks=[];bytes=0;recordedBlob=null;
      if (previewUrl) URL.revokeObjectURL(previewUrl);previewUrl=null;
      $("recordPreview").classList.add("hidden");$("recordUse").classList.add("hidden");
      recorder.addEventListener("dataavailable",e=>{if(e.data.size){chunks.push(e.data);bytes+=e.data.size;if(bytes>19*1024*1024)stopRecording();}});
      recorder.addEventListener("error",e=>{releaseMicrophone();recordingStatus("Ошибка записи: "+(e.error?.message || "микрофон недоступен"));$("recordStart").disabled=false;$("recordStop").disabled=true;});
      recorder.addEventListener("stop",()=>{
        const duration=(Date.now()-began)/1000;releaseMicrophone();
        $("recordStart").disabled=false;$("recordStop").disabled=true;$("recordAgain").disabled=false;
        if (!chunks.length || duration<1) {recordingStatus("Слишком коротко. Запиши хотя бы несколько секунд.");return;}
        recordedBlob=new Blob(chunks,{type:recorder.mimeType || type || "audio/webm"});
        previewUrl=URL.createObjectURL(recordedBlob);$("recordPreview").src=previewUrl;$("recordPreview").classList.remove("hidden");
        $("recordUse").classList.remove("hidden");$("recordUse").disabled=false;
        recordingStatus("Записано "+Math.round(duration)+" сек. Прослушай перед сохранением.");
      });
      recorder.start(500);began=Date.now();$("recordStop").disabled=false;
      recordingStatus("● Идёт запись" + (window.StudioLosslessRecorder ? " · чистый WAV PCM без Opus-сжатия" : " · режим совместимости браузера") + ". Микрофон выключится при остановке.");
      ticker=setInterval(()=>{const seconds=Math.floor((Date.now()-began)/1000);$("recordTimer").textContent=String(Math.floor(seconds/60)).padStart(2,"0")+":"+String(seconds%60).padStart(2,"0")+" / 03:00";if(seconds>=180)stopRecording();},200);
      try {audioContext=new (window.AudioContext || window.webkitAudioContext)();analyser=audioContext.createAnalyser();audioContext.createMediaStreamSource(stream).connect(analyser);showLevel();} catch (_) { /* Meter is optional; recording is independent. */ }
    } catch(e) {
      releaseMicrophone();$("recordStart").disabled=false;$("recordStop").disabled=true;
      const messages={NotAllowedError:"Разреши доступ к микрофону в браузере.",NotFoundError:"Микрофон не найден.",NotReadableError:"Микрофон занят другим приложением."};
      recordingStatus(messages[e.name] || e.message);notify(messages[e.name] || e.message,true);
    }
  }
  $("recordStart").addEventListener("click",startRecording);
  $("recordAgain").addEventListener("click",startRecording);
  $("recordStop").addEventListener("click",stopRecording);
  $("recordUse").addEventListener("click",async()=>{
    if(!recordedBlob)return;$("recordUse").disabled=true;recordingStatus("Сохраняем и проверяем уровень записи...");
    try {
      const result=await call("/api/recording",{method:"POST",headers:{"Content-Type":recordedBlob.type || "audio/webm"},body:recordedBlob});
      selectedVoice=result.name;await refreshVoices();$("voiceSelect").value=result.name;
      $("useVoice").checked=true;$("voiceChooser").classList.remove("hidden");saveDraft();
      recordingStatus("Сохранено: "+result.analysis.seconds+" сек. "+(result.analysis.warning || "Запись готова к использованию."));
      notify(result.analysis.warning || "Запись сохранена и выбрана для песни.");navigate("create");
    } catch(e) {recordingStatus(e.message);notify(e.message,true);$("recordUse").disabled=false;}
  });
  $("recordFromCreate").addEventListener("click",()=>{navigate("voices");if(window.studio34OpenVoiceWizard)window.studio34OpenVoiceWizard();else $("recordStart").focus();});
  window.addEventListener("pagehide",()=>{stopRecording();releaseMicrophone();if(previewUrl)URL.revokeObjectURL(previewUrl);saveDraft();});
})();
