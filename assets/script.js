const washPhases = [
  {step:1, duration:60, name:'Предварительный набор', text:'Открыт клапан холодной воды: бак получает воду перед циркуляцией.', outputs:['cold']},
  {step:2, duration:120, name:'Предварительная циркуляция', text:'Холодная вода подаётся через CIP-головку, помпа гонит поток по контуру.', outputs:['cold','pump']},
  {step:3, duration:120, name:'Циркуляция остатка', text:'Подача воды закрыта, помпа продолжает прогонять жидкость через распылитель.', outputs:['pump']},
  {step:4, duration:420, name:'Слив предмойки', text:'Открыт сливной клапан: отработанная вода уходит из нижней точки бака.', outputs:['drain']},
  {step:5, duration:60, name:'Набор щёлочного раствора', text:'Холодная и горячая вода смешиваются с щёлочью перед основным моющим циклом.', outputs:['cold','hot','alkali']},
  {step:6, duration:60, name:'Щёлочная CIP-мойка', text:'Щёлочной раствор подаётся через CIP-головку и омывает внутренние стенки.', outputs:['cold','hot','alkali','pump']},
  {step:7, duration:60, name:'Промывка после щёлочи', text:'Горячая и холодная вода идут через помпу без подачи щёлочи.', outputs:['cold','hot','pump']},
  {step:8, duration:120, name:'Циркуляция промывки', text:'Помпа прогоняет остаток раствора через распылительную головку.', outputs:['pump']},
  {step:9, duration:300, name:'Слив щёлочного этапа', text:'Отработанный раствор направляется в слив.', outputs:['drain']},
  {step:10, duration:300, name:'Дренажная выдержка', text:'Продолжение слива из нижней точки бака.', outputs:['drain']},
  {step:11, duration:180, name:'Водное ополаскивание', text:'Холодная и горячая вода подаются в контур, помпа распределяет поток по стенкам.', outputs:['cold','hot','pump']},
  {step:12, duration:120, name:'Циркуляция ополаскивания', text:'Подача воды закрыта, помпа завершает промывку контура.', outputs:['pump']},
  {step:13, duration:300, name:'Слив ополаскивания', text:'Вода после ополаскивания уходит в слив.', outputs:['drain']},
  {step:14, duration:300, name:'Дренажная выдержка', text:'Продолжение слива перед кислотным этапом.', outputs:['drain']},
  {step:15, duration:60, name:'Набор кислотного раствора', text:'Холодная и горячая вода смешиваются с кислотой для удаления минеральных отложений.', outputs:['cold','hot','acid']},
  {step:16, duration:60, name:'Кислотная CIP-мойка', text:'Кислотный раствор подаётся через CIP-головку и проходит по внутренним поверхностям.', outputs:['cold','hot','acid','pump']},
  {step:17, duration:60, name:'Промывка после кислоты', text:'Горячая и холодная вода идут через помпу без подачи кислоты.', outputs:['cold','hot','pump']},
  {step:18, duration:120, name:'Циркуляция промывки', text:'Помпа прогоняет остаток промывочной воды через распылитель.', outputs:['pump']},
  {step:19, duration:300, name:'Слив кислотного этапа', text:'Отработанная жидкость уходит через сливной клапан.', outputs:['drain']},
  {step:20, duration:300, name:'Дренажная выдержка', text:'Продолжение слива из нижней точки бака.', outputs:['drain']},
  {step:21, duration:180, name:'Финальное ополаскивание', text:'Вода подаётся через контур и помпу для удаления остатков реагентов.', outputs:['cold','hot','pump']},
  {step:22, duration:120, name:'Финальная циркуляция', text:'Помпа завершает промывку внутренних поверхностей.', outputs:['pump']},
  {step:23, duration:300, name:'Финальный слив', text:'Последняя вода уходит через сливной клапан.', outputs:['drain']},
  {step:24, duration:300, name:'Контрольный дренаж', text:'Финальная дренажная выдержка перед возвратом в ожидание.', outputs:['drain']},
  {step:25, duration:0, name:'Стоп', text:'Программа завершена: ХВ, ГВ, Щ, К, СЛ и П отключены.', outputs:[]}
];

const outputMeta = {
  cold:['❄️','ХВ','холодная вода'], hot:['🔥','ГВ','горячая вода'], alkali:['🧪','Щ','щёлочь'],
  acid:['⚗️','К','кислота'], drain:['🚰','СЛ','слив'], pump:['↻','П','помпа']
};
const kilnSteps = [
  {name:'Старт', temp:'25→120°', text:'мягкий нагрев'},
  {name:'Сушка', temp:'120°', text:'выдержка'},
  {name:'Разгон', temp:'120→650°', text:'основной нагрев'},
  {name:'Полка 1', temp:'650°', text:'стабилизация'},
  {name:'Финишный нагрев', temp:'650→980°', text:'выход на температуру'},
  {name:'Полка 2', temp:'980°', text:'обжиг'},
  {name:'Охлаждение', temp:'980→600°', text:'снижение температуры'},
  {name:'Финиш', temp:'600→80°', text:'завершение'}
];
function fmt(sec){if(!sec)return '0 сек';let m=Math.floor(sec/60),s=sec%60;return m?(s?`${m} мин ${s} сек`:`${m} мин`):`${sec} сек`;}
function initReveal(){const io=new IntersectionObserver(es=>es.forEach(e=>{if(e.isIntersecting){e.target.classList.add('visible');io.unobserve(e.target);}}),{threshold:.12});document.querySelectorAll('.reveal').forEach(x=>io.observe(x));}
function initWash(){
  const root=document.querySelector('[data-wash-widget]'); if(!root)return;
  let i=0,timer=null;
  root.innerHTML=`<div class="wash-ui cip-ui">
    <div class="cip-stage">
      <div class="cip-sources" aria-label="Источники">
        <div class="source source-cold" data-out="cold"><i>❄️</i><b>ХВ</b><small>холодная вода</small></div>
        <div class="source source-hot" data-out="hot"><i>🔥</i><b>ГВ</b><small>горячая вода</small></div>
        <div class="source source-alkali" data-out="alkali"><i>🧪</i><b>Щ</b><small>щёлочь</small></div>
        <div class="source source-acid" data-out="acid"><i>⚗️</i><b>К</b><small>кислота</small></div>
      </div>

      <div class="cip-lines">
        <div class="pipe pipe-cold"></div>
        <div class="pipe pipe-hot"></div>
        <div class="pipe pipe-alkali"></div>
        <div class="pipe pipe-acid"></div>
        <div class="pipe pipe-mix"></div>
        <div class="pipe pipe-feed"></div>
        <div class="pipe pipe-return"></div>
        <div class="pipe pipe-drain"></div>
      </div>

      <div class="mixing-node">
        <span class="mix-dot"></span>
        <b>смесительный узел</b>
      </div>

      <div class="milk-tank">
        <div class="tank-shadow"></div>
        <div class="tank-body">
          <div class="tank-end left"></div>
          <div class="tank-end right"></div>
          <div class="tank-top-nozzle">
            <span class="spray-ball"></span>
          </div>
          <div class="spray-cloud">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
          <div class="wall-film film-a"></div>
          <div class="wall-film film-b"></div>
          <div class="wash-pool">
            <span class="wave w1"></span><span class="wave w2"></span>
          </div>
          <div class="bottom-outlet"></div>
        </div>
        <div class="tank-label">молочный танк</div>
      </div>

      <div class="pump-unit" data-out="pump">
        <div class="pump-wheel">↻</div>
        <b>П</b><small>помпа</small>
      </div>

      <div class="drain-box" data-out="drain">
        <b>СЛ</b><small>слив</small>
        <div class="drain-water"></div>
      </div>

      <div class="controller-mini">
        <div class="screen"><span data-lcd-line1>РЕЖИМ МОЙКИ</span><span data-lcd-line2>----------------</span></div>
        <div class="ctrl-dots"><i></i><i></i><i></i></div>
      </div>
    </div>

    <div class="phase-panel">
      <div class="current-step">
        <div class="step-num"></div>
        <div>
          <h3></h3>
          <p></p>
          <div class="outputs"></div>
        </div>
      </div>
      <div class="phase-explain">
        <b data-flow-title></b>
        <p data-flow-text></p>
      </div>
      <div class="step-buttons"></div>
    </div>
  </div>`;
  const stepButtons=root.querySelector('.step-buttons');
  stepButtons.innerHTML=washPhases.map((p,idx)=>`<button type="button" data-i="${idx}">${p.step}</button>`).join('');

  function stop(){if(timer)clearInterval(timer);timer=null;document.querySelectorAll('[data-wash-run]').forEach(b=>b.textContent='Запустить');}
  function flowTitle(outs){
    if(!outs.length) return ['Ожидание','Все исполнительные выходы отключены. Контроллер возвращает систему в безопасное состояние.'];
    if(outs.includes('drain')) return ['Слив через нижнюю точку','Подача и циркуляция отключены, открыт сливной клапан. Отработанная жидкость уходит из танка самотёком.'];
    if(outs.includes('pump') && (outs.includes('alkali') || outs.includes('acid'))) return ['CIP через распылительную головку','Помпа подаёт моющий раствор на верхнюю CIP-головку: струи смачивают стенки, а жидкость возвращается в нижнюю часть контура.'];
    if(outs.includes('pump') && (outs.includes('cold') || outs.includes('hot'))) return ['Ополаскивание с циркуляцией','Вода поступает в контур, помпа прокачивает её через верхний распылитель и внутренние поверхности бака.'];
    if(outs.includes('pump')) return ['Рециркуляция остатка','Новые клапаны подачи закрыты, помпа гонит уже набранную жидкость по контуру распыления.'];
    return ['Набор раствора','Открыты входные клапаны. Жидкость проходит через смесительный узел, но помпа ещё не запущена.'];
  }
  function render(){
    const p=washPhases[i], outs=p.outputs;
    root.classList.toggle('is-cold',outs.includes('cold'));
    root.classList.toggle('is-hot',outs.includes('hot'));
    root.classList.toggle('is-alkali',outs.includes('alkali'));
    root.classList.toggle('is-acid',outs.includes('acid'));
    root.classList.toggle('is-pump',outs.includes('pump'));
    root.classList.toggle('is-drain',outs.includes('drain'));
    root.classList.toggle('is-stop',!outs.length);

    root.querySelector('.step-num').textContent=p.step;
    root.querySelector('.current-step h3').textContent=p.name+' · '+fmt(p.duration);
    root.querySelector('.current-step p').textContent=p.text;
    root.querySelector('.outputs').innerHTML=outs.length?outs.map(o=>`<span>${outputMeta[o][0]} ${outputMeta[o][1]} · ${outputMeta[o][2]}</span>`).join(''):'<span>все выходы отключены</span>';
    root.querySelectorAll('[data-out]').forEach(el=>el.classList.toggle('on',outs.includes(el.dataset.out)));

    const [title,txt]=flowTitle(outs);
    root.querySelector('[data-flow-title]').textContent=title;
    root.querySelector('[data-flow-text]').textContent=txt;

    root.querySelector('[data-lcd-line1]').textContent=p.step===25?'КОНЕЦ МОЙКИ':`ШАГ-${p.step} ${fmt(p.duration).toUpperCase()}`;
    const lcdOut=outs.map(o=>outputMeta[o][1]).join('  ');
    root.querySelector('[data-lcd-line2]').textContent=lcdOut || '----------------';

    const pool=root.querySelector('.wash-pool');
    pool.style.background=outs.includes('alkali')?'#55E6A5':outs.includes('acid')?'#B99CFF':outs.includes('hot')?'#FFB457':'#54D4FF';
    pool.style.height=outs.includes('drain')?'18px':outs.includes('pump')?'58px':outs.length?'38px':'10px';

    stepButtons.querySelectorAll('button').forEach((b,idx)=>b.classList.toggle('active',idx===i));
  }
  function next(){i=Math.min(i+1,washPhases.length-1);render();if(i===washPhases.length-1)stop();}
  function prev(){i=Math.max(i-1,0);render();}
  document.querySelectorAll('[data-wash-next]').forEach(b=>b.onclick=()=>{stop();next();});
  document.querySelectorAll('[data-wash-prev]').forEach(b=>b.onclick=()=>{stop();prev();});
  document.querySelectorAll('[data-wash-run]').forEach(b=>b.onclick=()=>{if(timer){stop();return;}if(i===washPhases.length-1){i=0;render();}b.textContent='Пауза';timer=setInterval(next,720);});
  stepButtons.onclick=e=>{if(e.target.matches('button')){stop();i=+e.target.dataset.i;render();}};
  render();
}
function initKiln(){
  const root=document.querySelector('[data-kiln-widget]'); if(!root)return; let i=0,timer=null;
  const pts='30,190 80,150 140,150 210,92 270,92 350,42 420,42 480,110 530,170';
  root.innerHTML=`<div class="kiln-ui"><div class="kiln-stage"><div class="kiln-box"><div class="kiln-door"><div class="flame"></div></div><div class="kiln-controller"><div class="kiln-display"></div></div></div></div><div><div class="kiln-chart"><svg viewBox="0 0 560 220"><path d="M30 190H530M30 145H530M30 100H530M30 55H530" stroke="#20324822" stroke-width="3"/><polyline points="${pts}" fill="none" stroke="#203248" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/><circle class="dot" cx="30" cy="190" r="12" fill="#FFB457" stroke="#203248" stroke-width="5"/></svg></div><div class="kiln-info"><h3></h3><p></p></div><div class="kiln-steps"></div></div></div>`;
  const points=[[30,190],[80,150],[140,150],[210,92],[270,92],[350,42],[420,42],[530,170]];
  const buttons=root.querySelector('.kiln-steps'); buttons.innerHTML=kilnSteps.map((s,idx)=>`<button data-i="${idx}">${idx+1}. ${s.name}</button>`).join('');
  function stop(){if(timer)clearInterval(timer);timer=null;document.querySelectorAll('[data-kiln-run]').forEach(b=>b.textContent='Запустить');}
  function render(){let s=kilnSteps[i],p=points[i];root.querySelector('.kiln-info h3').textContent=(i+1)+'. '+s.name;root.querySelector('.kiln-info p').textContent=s.temp+' · '+s.text;root.querySelector('.kiln-display').textContent=s.temp.split('→').pop();root.querySelector('.dot').setAttribute('cx',p[0]);root.querySelector('.dot').setAttribute('cy',p[1]);root.querySelector('.kiln-door').classList.toggle('hot',i>=2&&i<=5);buttons.querySelectorAll('button').forEach((b,idx)=>b.classList.toggle('active',idx===i));}
  function next(){i=Math.min(i+1,kilnSteps.length-1);render();if(i===kilnSteps.length-1)stop();} function prev(){i=Math.max(i-1,0);render();}
  document.querySelectorAll('[data-kiln-next]').forEach(b=>b.onclick=()=>{stop();next();});document.querySelectorAll('[data-kiln-prev]').forEach(b=>b.onclick=()=>{stop();prev();});
  document.querySelectorAll('[data-kiln-run]').forEach(b=>b.onclick=()=>{if(timer){stop();return;}if(i===kilnSteps.length-1){i=0;render();}b.textContent='Пауза';timer=setInterval(next,800);});
  buttons.onclick=e=>{if(e.target.matches('button')){stop();i=+e.target.dataset.i;render();}};render();
}
document.addEventListener('DOMContentLoaded',()=>{initReveal();initWash();initKiln();});

// v41: mobile header and KPMT scroll
(() => {
  const header = document.querySelector('.site-header');
  if (!header) return;

  let lastY = window.scrollY || 0;
  let upAccum = 0;
  let downAccum = 0;
  const hideThreshold = 38;
  const showThreshold = 86;

  const onScroll = () => {
    const y = window.scrollY || 0;
    const delta = y - lastY;

    if (y < 12) {
      header.classList.remove('header-hidden');
      upAccum = 0;
      downAccum = 0;
      lastY = y;
      return;
    }

    if (delta > 0) {
      downAccum += delta;
      upAccum = 0;
      if (downAccum > hideThreshold) {
        header.classList.add('header-hidden');
        downAccum = 0;
      }
    } else if (delta < 0) {
      upAccum += Math.abs(delta);
      downAccum = 0;
      if (upAccum > showThreshold) {
        header.classList.remove('header-hidden');
        upAccum = 0;
      }
    }

    lastY = y;
  };

  window.addEventListener('scroll', onScroll, { passive: true });
})();

(() => {
  const centerKpmt = () => {
    document.querySelectorAll('.kpmt-home-demo').forEach((el) => {
      if (el.scrollWidth <= el.clientWidth + 4) return;
      const max = el.scrollWidth - el.clientWidth;
      // На мобильном по умолчанию показываем не левую бочку, а блок "ПРОМЫВКА" с охладителем.
      el.scrollLeft = Math.min(max, Math.round(max * 0.82));
    });
  };

  window.addEventListener('load', centerKpmt, { once: true });
  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtCenterTimer);
    window.__kpmtCenterTimer = window.setTimeout(centerKpmt, 120);
  });
})();

// v42: exact KPMT centering
(() => {
  const centerKpmt = () => {
    document.querySelectorAll('.kpmt-home-demo').forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;
      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;

      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenterInScroll = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const nextLeft = Math.max(0, Math.min(box.scrollWidth - box.clientWidth, targetCenterInScroll - box.clientWidth / 2));

      box.scrollLeft = Math.round(nextLeft);
    });
  };

  window.addEventListener('load', () => {
    centerKpmt();
    window.setTimeout(centerKpmt, 250);
  }, { once: true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtExactCenterTimer);
    window.__kpmtExactCenterTimer = window.setTimeout(centerKpmt, 140);
  });
})();

// v43: mobile-only KPMT centering
(() => {
  const centerKpmtMobile = () => {
    if (!window.matchMedia('(max-width: 680px)').matches) return;

    document.querySelectorAll('.kpmt-home-demo:not(.product-kpmt-thumb)').forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;

      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;

      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenter = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const max = box.scrollWidth - box.clientWidth;
      const next = Math.max(0, Math.min(max, targetCenter - box.clientWidth / 2));

      box.scrollLeft = Math.round(next);
    });
  };

  window.addEventListener('load', () => {
    centerKpmtMobile();
    window.setTimeout(centerKpmtMobile, 250);
  }, { once: true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtMobileOnlyTimer);
    window.__kpmtMobileOnlyTimer = window.setTimeout(centerKpmtMobile, 140);
  });
})();

// v45: KPMT center only on main mobile
(() => {
  const centerMainKpmtMobile = () => {
    if (!window.matchMedia('(max-width: 680px)').matches) return;

    document.querySelectorAll('.section.split .image-link.kpmt-home-demo:not(.product-kpmt-exact):not(.product-kpmt-thumb)').forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;
      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;

      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenter = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const max = box.scrollWidth - box.clientWidth;
      const next = Math.max(0, Math.min(max, targetCenter - box.clientWidth / 2));
      box.scrollLeft = Math.round(next);
    });
  };

  window.addEventListener('load', () => {
    centerMainKpmtMobile();
    window.setTimeout(centerMainKpmtMobile, 250);
  }, { once: true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtV45CenterTimer);
    window.__kpmtV45CenterTimer = window.setTimeout(centerMainKpmtMobile, 140);
  });
})();

// v46: precise KPMT mobile centering
(() => {
  const centerMainKpmtMobile = () => {
    if (!window.matchMedia('(max-width: 680px)').matches) return;

    document.querySelectorAll('.section.split .image-link.kpmt-home-demo:not(.product-kpmt-exact):not(.product-kpmt-thumb)').forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;
      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;

      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenter = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const max = box.scrollWidth - box.clientWidth;
      const next = Math.max(0, Math.min(max, targetCenter - box.clientWidth / 2));
      box.scrollLeft = Math.round(next);
    });
  };

  window.addEventListener('load', () => {
    centerMainKpmtMobile();
    window.setTimeout(centerMainKpmtMobile, 180);
    window.setTimeout(centerMainKpmtMobile, 420);
  }, { once: true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtV46CenterTimer);
    window.__kpmtV46CenterTimer = window.setTimeout(centerMainKpmtMobile, 140);
  });
})();

// v47: robust KPMT mobile centering
(() => {
  const selector = '.section.split .image-link.kpmt-home-demo:not(.product-kpmt-exact):not(.product-kpmt-thumb)';

  const centerMobileKpmt = () => {
    if (!window.matchMedia('(max-width: 680px)').matches) return;

    document.querySelectorAll(selector).forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;

      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;

      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenter = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const max = box.scrollWidth - box.clientWidth;
      box.scrollLeft = Math.round(Math.max(0, Math.min(max, targetCenter - box.clientWidth / 2)));
    });
  };

  window.addEventListener('load', () => {
    centerMobileKpmt();
    window.setTimeout(centerMobileKpmt, 250);
  }, { once:true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtV47Timer);
    window.__kpmtV47Timer = window.setTimeout(centerMobileKpmt, 140);
  });
})();

// v49: focus detail KPMT on mobile
(() => {
  const focusDetailKpmt = () => {
    if (!window.matchMedia('(max-width: 680px)').matches) return;
    document.querySelectorAll('.product-hero .kpmt-detail-visual').forEach((box) => {
      if (box.scrollWidth <= box.clientWidth + 4) return;
      const target = box.querySelector('.kpmt-controller') || box.querySelector('.cooling-unit');
      if (!target) return;
      const boxRect = box.getBoundingClientRect();
      const targetRect = target.getBoundingClientRect();
      const targetCenter = (targetRect.left - boxRect.left) + box.scrollLeft + targetRect.width / 2;
      const max = box.scrollWidth - box.clientWidth;
      box.scrollLeft = Math.round(Math.max(0, Math.min(max, targetCenter - box.clientWidth / 2)));
    });
  };

  window.addEventListener('load', () => {
    focusDetailKpmt();
    window.setTimeout(focusDetailKpmt, 250);
  }, { once:true });

  window.addEventListener('resize', () => {
    window.clearTimeout(window.__kpmtDetailFocusTimer);
    window.__kpmtDetailFocusTimer = window.setTimeout(focusDetailKpmt, 140);
  });
})();
