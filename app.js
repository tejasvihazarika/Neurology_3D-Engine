import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

let loretaData = null, brainScene = null;
const REGION_COLORS = { Frontal:'#2563EB', Parietal:'#7C3AED', Temporal:'#0891B2', Occipital:'#DC2626' };
const BAND_COLORS = { Delta:'#6366F1', Theta:'#0891B2', Alpha:'#059669', Beta:'#D97706', Gamma:'#DC2626' };
const lightLayout = (extra={}) => ({
    margin:{t:25,l:50,r:20,b:40}, paper_bgcolor:'transparent', plot_bgcolor:'transparent',
    font:{color:'#6B7280',family:'Inter',size:12},
    xaxis:{gridcolor:'#F3F4F6',zerolinecolor:'#E5E7EB',...extra.xaxis},
    yaxis:{gridcolor:'#F3F4F6',zerolinecolor:'#E5E7EB',...extra.yaxis}, ...extra
});
const pCfg = {responsive:true,displayModeBar:false};

// ─── NAV ─── //
document.querySelectorAll('.nav-item[data-target]').forEach(link => {
    link.addEventListener('click', e => {
        e.preventDefault();
        document.querySelectorAll('.nav-item[data-target]').forEach(n=>n.classList.remove('active'));
        link.classList.add('active');
        document.querySelectorAll('.view-content').forEach(s=>{s.classList.add('hidden');s.classList.remove('active')});
        const t=document.getElementById(link.dataset.target);
        if(t){t.classList.remove('hidden');t.classList.add('active')}
        window.dispatchEvent(new Event('resize'));
        if(link.dataset.target==='3dbrain-view'&&!brainScene) initBrain3D();
    });
});

// ─── LOAD ─── //
fetch('loreta_results.json').then(r=>r.json()).then(data=>{
    loretaData=data; renderDashboard(); renderDataset(); renderProcessing();
    renderAnalytics(); render2DViz(); renderComparison(); renderReport(); renderGlossary();
}).catch(e=>console.error('Load error',e));

// ─── 1. DASHBOARD ─── //
function renderDashboard(){
    const d=loretaData, s=d.global_stats;
    document.getElementById('dash-channels').textContent=s.total_channels;
    document.getElementById('dash-sr').textContent=s.sampling_rate+' Hz';
    document.getElementById('dash-duration').textContent=s.duration_seconds+' sec';
    document.getElementById('dash-class').textContent=d.classification.label;
    document.getElementById('dash-dom-band').textContent=d.frequency_bands.dominant+' waves';

    const steps=[{name:'Record Signals',key:'raw_eeg'},{name:'Break Down (FFT)',key:'fft'},
        {name:'Find Wave Types',key:'frequency_bands'},{name:'Locate Source',key:'loreta'},{name:'Identify Activity',key:'classification'}];
    document.getElementById('pipeline-flow').innerHTML=steps.map((s,i)=>{
        const done=d.pipeline_status[s.key]==='complete';
        return (i>0?`<div class="step-line ${done?'done':''}"></div>`:'')+
        `<div class="pipeline-step"><div class="step-icon ${done?'done':''}"><svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg></div><span class="step-name">${s.name}</span><span class="badge done">Done</span></div>`;
    }).join('');

    // Region bar chart (replaced donut for clarity)
    const rp=d.loreta_results.region_percentages;
    Plotly.newPlot('dash-region-chart',[{
        x:Object.keys(rp), y:Object.values(rp), type:'bar',
        marker:{color:Object.keys(rp).map(r=>REGION_COLORS[r])},
        text:Object.values(rp).map(v=>v+'%'), textposition:'auto', textfont:{color:'#1F2937',size:13}
    }],lightLayout({xaxis:{title:'Brain Region'},yaxis:{title:'Activity (%)',range:[0,50]}}),pCfg);
}

// ─── 2. DATASET ─── //
function renderDataset(){
    const s=loretaData.global_stats;
    document.getElementById('dataset-info-list').innerHTML=[
        ['Sensors (Channels)',s.total_channels],['Readings Per Second',s.sampling_rate+' Hz'],
        ['Recording Length',s.duration_seconds+' sec'],['Total Data Points',s.total_samples],['Subject State','Resting (Eyes Closed)']
    ].map(([l,v])=>`<li><span class="label">${l}</span><span class="value">${v}</span></li>`).join('');

    document.getElementById('global-stats-grid').innerHTML=[
        ['AVERAGE SIGNAL',s.mean_signal+' μV'],['SIGNAL SPREAD',s.variance+' μV²'],
        ['HIGHEST PEAK',`<span class="text-red">${s.max_amplitude} μV</span>`],
        ['LOWEST DIP',`<span class="text-blue">${s.min_amplitude} μV</span>`]
    ].map(([l,v])=>`<div class="stat-item"><span class="label">${l}</span><span class="value">${v}</span></div>`).join('');

    const traces=[];
    Object.entries(loretaData.fft_spectrum).forEach(([ch,d])=>{
        traces.push({x:d.frequencies,y:d.magnitude,mode:'lines',name:ch+' sensor',line:{width:2}});
    });
    Plotly.newPlot('full-waveform-chart',traces,lightLayout({xaxis:{title:'Frequency (Hz)'},yaxis:{title:'Signal Strength'}}),pCfg);
}

// ─── 3. PROCESSING ─── //
function renderProcessing(){
    const traces=[];
    Object.entries(loretaData.fft_spectrum).forEach(([ch,d])=>{
        traces.push({x:d.frequencies,y:d.magnitude,type:'scatter',mode:'lines',name:ch,line:{width:2}});
    });
    Plotly.newPlot('fft-chart',traces,lightLayout({xaxis:{title:'Frequency (Hz)'},yaxis:{title:'Signal Strength'}}),pCfg);

    const bd=loretaData.frequency_bands.distribution;
    Plotly.newPlot('band-dist-chart',[{
        x:Object.keys(bd),y:Object.values(bd),type:'bar',
        marker:{color:Object.keys(bd).map(b=>BAND_COLORS[b])},
        text:Object.values(bd).map(v=>v+'%'),textposition:'auto',textfont:{color:'#1F2937'}
    }],lightLayout({xaxis:{title:'Wave Type'},yaxis:{title:'Strength (%)'}}),pCfg);

    const rp=loretaData.loreta_results.region_percentages;
    Plotly.newPlot('region-map-chart',[{
        x:Object.keys(rp),y:Object.values(rp),type:'bar',
        marker:{color:Object.keys(rp).map(r=>REGION_COLORS[r])},
        text:Object.values(rp).map(v=>v+'%'),textposition:'auto',textfont:{color:'#1F2937'}
    }],lightLayout({xaxis:{title:'Brain Area'},yaxis:{title:'Activity (%)'}}),pCfg);
}

// ─── 4. 3D BRAIN ─── //
function initBrain3D(){
    const container=document.getElementById('brain-3d-container');
    const w=container.clientWidth,h=container.clientHeight;
    const scene=new THREE.Scene();
    scene.background=new THREE.Color(0xF0F4FF);
    const camera=new THREE.PerspectiveCamera(45,w/h,0.1,100);
    camera.position.set(0,0.8,3);
    const renderer=new THREE.WebGLRenderer({antialias:true});
    renderer.setSize(w,h); renderer.setPixelRatio(Math.min(window.devicePixelRatio,2));
    renderer.outputColorSpace=THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);
    const controls=new OrbitControls(camera,renderer.domElement);
    controls.enableDamping=true; controls.dampingFactor=0.08;
    controls.minDistance=1; controls.maxDistance=8;

    scene.add(new THREE.AmbientLight(0xffffff,0.7));
    const dl=new THREE.DirectionalLight(0xffffff,1.0); dl.position.set(3,5,4); scene.add(dl);
    const dl2=new THREE.DirectionalLight(0x7C3AED,0.3); dl2.position.set(-3,-2,-3); scene.add(dl2);

    const loader=new GLTFLoader();
    loader.load('brain_model.glb',(gltf)=>{
        const model=gltf.scene;
        const box=new THREE.Box3().setFromObject(model);
        const center=box.getCenter(new THREE.Vector3());
        const size=box.getSize(new THREE.Vector3());
        const scale=2.0/Math.max(size.x,size.y,size.z);
        model.scale.setScalar(scale);
        model.position.sub(center.multiplyScalar(scale));

        const ri=loretaData.loreta_results.region_intensity;
        model.traverse(child=>{
            if(!child.isMesh) return;
            const geo=child.geometry, posAttr=geo.attributes.position;
            const colors=new Float32Array(posAttr.count*3);
            const bb=new THREE.Box3().setFromBufferAttribute(posAttr);
            const rangeY=bb.max.y-bb.min.y, rangeZ=bb.max.z-bb.min.z;

            for(let i=0;i<posAttr.count;i++){
                const normY=(posAttr.getY(i)-bb.min.y)/rangeY;
                const normZ=(posAttr.getZ(i)-bb.min.z)/rangeZ;
                let intensity=0.3, region='Parietal';
                if(normZ>0.6){intensity=ri.Frontal;region='Frontal';}
                else if(normZ<0.3){intensity=ri.Occipital;region='Occipital';}
                else if(normY>0.5){intensity=ri.Parietal;region='Parietal';}
                else{intensity=ri.Temporal;region='Temporal';}

                // Warm-cool: blue(low) → green(mid) → orange(high) → red(very high)
                const c=new THREE.Color();
                if(intensity<0.4) c.setRGB(0.35+intensity,0.55+intensity*0.5,0.9-intensity);
                else if(intensity<0.7) c.setRGB(0.2+intensity*0.8,0.75-intensity*0.2,0.3);
                else c.setRGB(0.9,0.35-intensity*0.15,0.15+intensity*0.1);
                colors[i*3]=c.r; colors[i*3+1]=c.g; colors[i*3+2]=c.b;
            }
            geo.setAttribute('color',new THREE.BufferAttribute(colors,3));
            child.material=new THREE.MeshStandardMaterial({vertexColors:true,metalness:0.05,roughness:0.65,transparent:true,opacity:0.93});
        });
        scene.add(model);
        brainScene={scene,camera,renderer,controls,model};
    },undefined,(err)=>{
        console.error('Model error:',err); createFallbackBrain(scene);
        brainScene={scene,camera,renderer,controls};
    });

    (function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera)})();
    window.addEventListener('resize',()=>{
        const w2=container.clientWidth,h2=container.clientHeight;
        if(w2&&h2){camera.aspect=w2/h2;camera.updateProjectionMatrix();renderer.setSize(w2,h2)}
    });
    document.getElementById('btn-reset-view')?.addEventListener('click',()=>{
        camera.position.set(0,0.8,3);controls.target.set(0,0,0);controls.update();
    });
    renderBrainSidebar();
}

function createFallbackBrain(scene){
    const ri=loretaData.loreta_results.region_intensity;
    [{name:'Frontal',pos:[0,0.3,0.6],i:ri.Frontal},{name:'Parietal',pos:[0,0.5,0],i:ri.Parietal},
     {name:'Temporal',pos:[0.6,-0.1,0],i:ri.Temporal},{name:'Occipital',pos:[0,0.1,-0.6],i:ri.Occipital}
    ].forEach(r=>{
        const c=new THREE.Color(); c.setHSL(0.6-r.i*0.5,0.7,0.5);
        const m=new THREE.Mesh(new THREE.SphereGeometry(0.35,24,24),
            new THREE.MeshStandardMaterial({color:c,transparent:true,opacity:0.8}));
        m.position.set(...r.pos); scene.add(m);
    });
}

function renderBrainSidebar(){
    const cl=loretaData.classification;
    document.getElementById('brain-classification').innerHTML=`
        <div class="cls-label">${cl.label}</div>
        <div class="cls-desc">${cl.description}</div>
        <div class="cls-confidence">Confidence: ${cl.confidence}%</div>
        <div class="confidence-bar"><div class="confidence-fill" style="width:${cl.confidence}%"></div></div>`;
    const rp=loretaData.loreta_results.region_percentages;
    document.getElementById('brain-legend').innerHTML=Object.entries(rp).map(([r,p])=>
        `<div class="region-legend-item"><div class="region-legend-left"><div class="region-dot" style="background:${REGION_COLORS[r]}"></div><span class="region-name">${r}</span></div><span class="region-pct">${p}%</span></div>`).join('');
}

// ─── 5. ANALYTICS ─── //
function renderAnalytics(){
    const cl=loretaData.classification;
    const cards=[
        {label:'MOST ACTIVE AREA',value:cl.dominant_region,sub:'Highest brain activity',color:REGION_COLORS[cl.dominant_region]},
        {label:'STRONGEST WAVE',value:cl.dominant_band,sub:'Most powerful frequency',color:BAND_COLORS[cl.dominant_band]},
        {label:'BRAIN STATE',value:cl.label,sub:cl.confidence+'% sure',color:'#0891B2'},
        {label:'SENSORS USED',value:loretaData.global_stats.total_channels,sub:'Placed on scalp',color:'#059669'}
    ];
    document.getElementById('analytics-cards').innerHTML=cards.map(c=>
        `<div class="card analytics-card"><div class="ac-label">${c.label}</div><div class="ac-value" style="color:${c.color}">${c.value}</div><div class="ac-sub">${c.sub}</div></div>`).join('');

    const rp=loretaData.loreta_results.region_percentages;
    Plotly.newPlot('analytics-region-chart',[{
        values:Object.values(rp),labels:Object.keys(rp),type:'pie',hole:0.4,
        marker:{colors:Object.keys(rp).map(r=>REGION_COLORS[r])},textfont:{color:'#1F2937'}
    }],lightLayout({showlegend:true,legend:{font:{color:'#6B7280'}}}),pCfg);

    const ra=loretaData.loreta_results.region_activity;
    const traces=Object.keys(BAND_COLORS).map(b=>({
        x:Object.keys(ra),y:Object.values(ra).map(r=>r[b]||0),name:b,type:'bar',marker:{color:BAND_COLORS[b]}
    }));
    Plotly.newPlot('analytics-band-region-chart',traces,lightLayout({barmode:'group',xaxis:{title:'Brain Area'},yaxis:{title:'Power'}}),pCfg);
}

// ─── 6. CHARTS (2D VIZ) ─── //
function render2DViz(){
    const bd=loretaData.frequency_bands.distribution;
    Plotly.newPlot('viz2d-bands',[{
        x:Object.keys(bd),y:Object.values(bd),type:'bar',
        marker:{color:Object.keys(bd).map(b=>BAND_COLORS[b])},
        text:Object.values(bd).map(v=>v+'%'),textposition:'auto',textfont:{color:'#1F2937'}
    }],lightLayout({xaxis:{title:'Wave Type'},yaxis:{title:'Strength (%)'}}),pCfg);

    // Simple horizontal bar for regions (replaced radar)
    const rp=loretaData.loreta_results.region_percentages;
    Plotly.newPlot('viz2d-regions',[{
        y:Object.keys(rp),x:Object.values(rp),type:'bar',orientation:'h',
        marker:{color:Object.keys(rp).map(r=>REGION_COLORS[r])},
        text:Object.values(rp).map(v=>v+'%'),textposition:'auto',textfont:{color:'#1F2937'}
    }],lightLayout({yaxis:{title:''},xaxis:{title:'Activity (%)'}}),pCfg);
}

// ─── 7. COMPARISON ─── //
function renderComparison(){
    const comp=loretaData.comparison;
    ['first_half','second_half'].forEach((seg,i)=>{
        const d=comp[seg],regions=Object.keys(d).filter(k=>k!=='dominant');
        Plotly.newPlot(`comp-seg${i+1}`,[{
            x:regions,y:regions.map(r=>d[r]),type:'bar',
            marker:{color:regions.map(r=>REGION_COLORS[r])},
            text:regions.map(r=>d[r]+'%'),textposition:'auto',textfont:{color:'#1F2937'}
        }],lightLayout({xaxis:{title:'Brain Area'},yaxis:{title:'Activity (%)',range:[0,60]}}),pCfg);
    });

    // Slider-based diff
    const regions=['Frontal','Parietal','Temporal','Occipital'];
    const sl=document.getElementById('comp-slider');
    const labels=document.getElementById('slider-labels');
    labels.innerHTML=regions.map((r,i)=>`<span class="${i===0?'active-label':''}">${r}</span>`).join('');

    function updateDetail(idx){
        const r=regions[idx];
        const v1=comp.first_half[r]||0,v2=comp.second_half[r]||0;
        const diff=v2-v1; const isPos=diff>=0;
        document.getElementById('comp-diff-detail').innerHTML=`
            <div class="cd-region" style="color:${REGION_COLORS[r]}">${r} Lobe</div>
            <div class="cd-bars">
                <div class="cd-bar-wrap"><div class="cd-bar-label">First Half</div><div class="cd-bar" style="width:${v1*2}%;background:${REGION_COLORS[r]}90;max-width:100%"></div><span style="font-size:0.82rem;font-weight:600">${v1}%</span></div>
                <div class="cd-bar-wrap"><div class="cd-bar-label">Second Half</div><div class="cd-bar" style="width:${v2*2}%;background:${REGION_COLORS[r]};max-width:100%"></div><span style="font-size:0.82rem;font-weight:600">${v2}%</span></div>
            </div>
            <div><span class="cd-change ${isPos?'positive':'negative'}">${isPos?'+':''}${diff.toFixed(1)}% change</span></div>`;
        labels.querySelectorAll('span').forEach((s,i)=>{s.classList.toggle('active-label',i===idx)});
    }
    sl.addEventListener('input',()=>updateDetail(parseInt(sl.value)));
    updateDetail(0);
}

// ─── 8. REPORT ─── //
function renderReport(){
    const d=loretaData,cl=d.classification,gs=d.global_stats,rp=d.loreta_results.region_percentages;
    document.getElementById('report-content').innerHTML=`
        <div class="card report-section"><h3>What Was Recorded</h3>
            <div class="report-grid">
                <div class="report-item"><div class="ri-label">Sensors</div><div class="ri-value">${gs.total_channels} placed on the scalp</div></div>
                <div class="report-item"><div class="ri-label">Speed</div><div class="ri-value">${gs.sampling_rate} readings per second</div></div>
                <div class="report-item"><div class="ri-label">Length</div><div class="ri-value">${gs.duration_seconds} seconds</div></div>
                <div class="report-item"><div class="ri-label">Data Points</div><div class="ri-value">${gs.total_samples} measurements</div></div>
            </div></div>
        <div class="card report-section"><h3>Brain Activity by Region</h3>
            <div class="report-grid">${Object.entries(rp).map(([r,p])=>`<div class="report-item"><div class="ri-label">${r} Lobe</div><div class="ri-value" style="color:${REGION_COLORS[r]}">${p}% active</div></div>`).join('')}</div></div>
        <div class="card report-section"><h3>What We Think the Brain Was Doing</h3>
            <div class="finding-card"><p><strong style="color:#2563EB">${cl.label}</strong> — ${cl.description}</p>
            <p style="margin-top:6px">Most active area: <strong>${cl.dominant_region}</strong> | Strongest wave: <strong>${cl.dominant_band}</strong> | We are <strong>${cl.confidence}%</strong> sure about this.</p></div></div>
        <div class="card report-section"><h3>Main Takeaways</h3>
            <div class="finding-card"><p>1. The brain was mainly producing <strong>${cl.dominant_band}</strong> waves, which usually means the person was in a <strong>${cl.label.toLowerCase()}</strong> state.</p></div>
            <div class="finding-card"><p>2. The <strong>${cl.dominant_region}</strong> part of the brain was most active (${rp[cl.dominant_region]}%), which handles ${cl.dominant_region==='Frontal'?'thinking and decisions':cl.dominant_region==='Temporal'?'hearing and memory':cl.dominant_region==='Parietal'?'touch and space awareness':'seeing things'}.</p></div>
            <div class="finding-card"><p>3. The signals ranged from ${gs.min_amplitude} to ${gs.max_amplitude} μV (microvolts), which is normal for brain recordings.</p></div></div>`;
}

// ─── 9. GLOSSARY ─── //
function renderGlossary(){
    const terms=[
        {term:'EEG (Electroencephalogram)',def:'A way to record the brain\'s electrical activity using small sensors placed on the scalp. It\'s painless and non-invasive — like wearing a special cap.'},
        {term:'Electrode / Sensor',def:'A small metal disc placed on the head to pick up electrical signals from the brain. Our recording used 61 sensors.'},
        {term:'Sampling Rate (Hz)',def:'How many times per second we take a reading. "32 Hz" means 32 snapshots of brain activity every second.'},
        {term:'FFT (Fast Fourier Transform)',def:'A math trick that breaks a complex signal into simpler wave patterns. Like splitting white light into a rainbow of colors.'},
        {term:'Frequency Band',def:'A group of brain waves at similar speeds. The main types are Delta (very slow), Theta (slow), Alpha (medium), Beta (fast), and Gamma (very fast).'},
        {term:'Delta Waves (0.5–4 Hz)',def:'Very slow brain waves. Usually seen during deep sleep. If these are dominant, the person is probably in deep rest.'},
        {term:'Theta Waves (4–8 Hz)',def:'Slow waves linked to drowsiness, light sleep, or daydreaming. Also appear during memory processing.'},
        {term:'Alpha Waves (8–13 Hz)',def:'Medium-speed waves that appear when you\'re relaxed but awake, especially with eyes closed. Common in the back of the head.'},
        {term:'Beta Waves (13–30 Hz)',def:'Faster waves associated with active thinking, focus, and problem-solving. Usually strongest in the front of the brain.'},
        {term:'Gamma Waves (30–45 Hz)',def:'The fastest brain waves. Related to intense concentration, learning, and processing complex information.'},
        {term:'LORETA (Source Localization)',def:'A method to estimate WHERE inside the brain the electrical activity is coming from, based on the signals recorded on the scalp surface.'},
        {term:'Frontal Lobe',def:'The front part of the brain. Handles thinking, planning, decision-making, and personality. It\'s like the brain\'s CEO.'},
        {term:'Parietal Lobe',def:'The top-middle area. Processes touch, temperature, and spatial awareness — helps you know where your body is in space.'},
        {term:'Temporal Lobe',def:'The sides of the brain, near the ears. Handles hearing, language understanding, and memory storage.'},
        {term:'Occipital Lobe',def:'The back of the brain. Dedicated to processing everything you see — colors, shapes, and movement.'},
        {term:'Amplitude (μV)',def:'How strong a signal is, measured in microvolts (μV). Higher amplitude = stronger brain activity at that moment.'},
        {term:'Baseline Correction',def:'Removing unwanted drift from the signal so we can see the real brain activity more clearly. Like leveling a photo that was taken tilted.'},
        {term:'Confidence Level',def:'How sure our system is about its classification. 92% means we\'re quite confident, but there\'s still a small chance the interpretation could be different.'},
    ];
    document.getElementById('glossary-content').innerHTML=terms.map(t=>
        `<div class="card glossary-item"><h4>${t.term}</h4><p>${t.def}</p></div>`).join('');
}
