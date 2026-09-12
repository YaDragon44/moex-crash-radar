// TA Market R0.8.4 production safety patch.
// Keeps the compact UI while enforcing global snapshot freshness and conservative scoring.
(function(){
  const originalAnalyze = window.analyze;
  if (typeof originalAnalyze === 'function') {
    window.analyze = function(id){
      const a = originalAnalyze(id);
      if (!a || !a.plan) return a;
      const t = Date.parse(J?.generated_at || '');
      const age = Number.isFinite(t) ? (Date.now() - t) / 60000 : Infinity;
      const snapshotFresh = age >= 0 && age <= 25;
      a.plan.checks = {...(a.plan.checks || {}), snapshot:snapshotFresh};
      if (!snapshotFresh && a.plan.status === 'READY') {
        a.plan.status = 'WAIT';
        a.plan.reason = 'STALE snapshot';
      }
      return a;
    };
    // Rebind the global identifier used by existing render/card functions.
    analyze = window.analyze;
  }

  // Exact 19-point rubric, conservative for unavailable components.
  // HTF trend, Wyckoff, Elliott and Relative Strength are currently unavailable => 0.
  window.score = function(a){
    if (!a || a.plan?.dir === 'NEUTRAL') return 0;
    let s = 0;
    // HTF trend 0/2: unavailable in compact UI.
    // Structure 0-2.
    if ((a.plan.dir === 'LONG' && a.st?.label === 'HH / HL') ||
        (a.plan.dir === 'SHORT' && a.st?.label === 'LH / LL')) s += 2;
    // Level 0-2.
    if (Number.isFinite(+a.plan?.entry) && Number.isFinite(+a.plan?.stop)) s += 2;
    // Volume/VSA 0-2: only RVOL is available, so require confirmation for 2.
    if (a.plan?.checks?.rvol) s += 2;
    // Wyckoff 0/1: unavailable.
    // Elliott 0/1: unavailable.
    // Fibonacci 0-1.
    if (a.fi) s += 1;
    // VWAP/Profile 0-1: profile available; VWAP unavailable.
    if (a.pr) s += 1;
    // Momentum 0-1.
    if (a.plan?.checks?.momentum) s += 1;
    // Relative Strength 0/1: unavailable.
    // R/R 0-3.
    const rr = +a.plan?.rr;
    if (Number.isFinite(rr)) s += rr >= 3 ? 3 : rr >= 2 ? 2 : rr >= 1 ? 1 : 0;
    // Market/sector 0-2. Sector is unavailable, so award only when market filter passes.
    if (a.plan?.checks?.market) s += 2;
    return Math.min(19, s);
  };
  score = window.score;

  document.title = 'TA Market Monitor · R0.8.4';
  const badge = document.querySelector('.top h1 .ok');
  if (badge) badge.textContent = 'R0.8.4';
  const footer = document.querySelector('.footer');
  if (footer) footer.innerHTML += '<br>R0.8.4: global snapshot age ≤25m is a hard READY gate. Confluence Score uses the approved 19-point rubric; unavailable components score 0.';
  setTimeout(function(){ if (window.J) render(); }, 500);
})();
