"use strict";
(() => {
  const page=document.querySelector("#page-settings .single-content");
  if(!page||document.getElementById("training41-card"))return;
  const section=document.createElement("section");
  section.className="card training41-card";
  section.id="training41-card";
  section.innerHTML='<div class="section-row"><div><h2>Обучение музыкальной модели</h2><p>Экспериментальная LoRA на собственных треках. Действующая модель защищена.</p></div><span class="training41-badge" id="training41-badge">Проверка</span></div><div class="training41-details"><p id="training41-stage">Проверяем состояние…</p><p id="training41-progress"></p><p class="field-hint">Во время обучения видеокарта занята, создание новых песен временно недоступно. Библиотека и прослушивание продолжают работать.</p></div><button class="secondary-button" type="button" id="training41-refresh">Обновить состояние</button>';
  page.append(section);
  const show=(id,s)=>{const e=document.getElementById(id);if(e)e.textContent=s};
  async function update(){
   try{
    const r=await fetch("/api/training41",{cache:"no-store"}),st=await r.json();
    if(!r.ok)throw Error(st.error||"Нет ответа");
    const names={not_started:"Не запущено",preflight:"Подготовка",preprocessing:"Создание обучающих данных",training:"Обучение LoRA",evaluating:"Проверка качества",completed:"Адаптер сохранён отдельно",failed:"Ошибка обучения",cancelled:"Остановлено"};
    show("training41-badge",st.active?"Обучение идёт":(names[st.stage]||st.stage));
    show("training41-stage",st.details||(names[st.stage]||"Нет обучения"));
    show("training41-progress",st.total>0?st.step+" / "+st.total+" шагов":"Рабочие треки, голоса и модель не перезаписываются.");
    section.dataset.state=st.active?"active":st.stage;
   }catch(e){show("training41-stage","Статус недоступен: "+e.message)}
  }
  document.getElementById("training41-refresh").addEventListener("click",update);
  update();setInterval(()=>{if(document.querySelector("#page-settings.page.visible"))update()},10000);
})();
