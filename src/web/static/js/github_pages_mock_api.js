/**
 * GitHub Pages Mock API Layer
 * 
 * GitHub Pages 정적 호스팅 환경(서버리스)에서
 * 프로토타입 실사용 검증, 타이머/하트비트, 피드백 등록, 파이프라인 시뮬레이션 등이
 * 100% 정상 작동하도록 클라이언트 사이드 fetch 요청을 가로채고 로컬 스토리지를 활용합니다.
 */
(function() {
  const isGitHubPages = window.location.hostname.endsWith('github.io') || 
                        window.location.protocol === 'file:' || 
                        window.__STATIC_EXPORT__ === true;

  if (!isGitHubPages) {
    // 로컬 FastAPI 서버 환경에서는 동작하지 않음
    return;
  }

  console.log('🚀 [모두의 창업비서 SSA] GitHub Pages 정적 모의 API 레이어 활성화');

  const origFetch = window.fetch;

  window.fetch = async function(input, init) {
    let url = typeof input === 'string' ? input : (input.url || '');
    const method = (init && init.method) ? init.method.toUpperCase() : 'GET';
    const bodyText = (init && init.body) ? (typeof init.body === 'string' ? init.body : '') : '';

    // URL에서 쿼리스트링 분리
    const [path, queryString] = url.split('?');

    // 1. 프로토타입 세션 시작
    if (path.includes('/api/prototype/sessions/start')) {
      const sessionId = 'gh_sess_' + Math.random().toString(36).substring(2, 9);
      return new Response(JSON.stringify({
        session_id: sessionId,
        status: 'STARTED',
        message: 'GitHub Pages 정적 데모 세션이 시작되었습니다.'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 2. 프로토타입 하트비트
    if (path.includes('/api/prototype/sessions/heartbeat')) {
      return new Response(JSON.stringify({
        ok: true,
        status: 'ENGAGED',
        active_seconds: 30
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 3. 프로토타입 피드백 제출
    if (path.includes('/api/prototype/feedback/submit')) {
      try {
        const payload = bodyText ? JSON.parse(bodyText) : {};
        const saved = JSON.parse(localStorage.getItem('ssa_prototype_feedbacks') || '[]');
        saved.unshift({
          ...payload,
          id: 'fb_' + Date.now(),
          created_at: new Date().toISOString().replace('T', ' ').substring(0, 19)
        });
        localStorage.setItem('ssa_prototype_feedbacks', JSON.stringify(saved));
      } catch (e) {
        console.warn('LocalStorage save fallback error:', e);
      }

      return new Response(JSON.stringify({
        ok: true,
        status: 'APPROVED',
        message: '모두의 창업비서(SSA) 피드백이 정상 등록되었습니다! (GitHub Pages 데모)'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 4. 파이프라인 수동 실행
    if (path.includes('/api/pipeline/run')) {
      return new Response(JSON.stringify({
        ok: true,
        items_processed: 4,
        announcements_evaluated: 5,
        total_matched: 1,
        message: '2026 정부지원사업 일일 파이프라인 검증이 정상 완료되었습니다. (시뮬레이션)',
        item_details: [
          { item_name: "2026년 탄소배출권 디지털 MRV 및 에너지 AX 실증과제", matched_count: 1 }
        ]
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 5. 소셜 로그인
    if (path.includes('/api/auth/social-login')) {
      return new Response(JSON.stringify({
        ok: true,
        user: { name: '대표 창업자', email: 'founder@startup.kr', role: 'subscriber' },
        message: '모두의 창업비서(SSA) 로그인 완료'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 6. 권한 변경
    if (path.includes('/api/auth/role')) {
      return new Response(JSON.stringify({ ok: true }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 7. 결제 체크아웃
    if (path.includes('/api/billing/checkout')) {
      return new Response(JSON.stringify({
        ok: true,
        checkout_url: './feedback_lounge.html'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 8. 스케줄러 토글
    if (path.includes('/api/scheduler/toggle')) {
      return new Response(JSON.stringify({
        ok: true,
        is_running: true,
        next_run_at: '2026-10-30 09:00:00'
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 9. 포털 핑
    if (path.includes('/api/portals/ping')) {
      return new Response(JSON.stringify({
        ok: true,
        status: 'UP',
        latency_ms: 45
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 10. 프로파일 조회
    if (path.includes('/api/profile')) {
      return new Response(JSON.stringify({
        company_name: "(주)에스케치 에이아이",
        biz_reg_no: "123-45-67890",
        target_tracks: ["창업중심대학", "초기창업패키지", "TIPS"]
      }), { status: 200, headers: { 'Content-Type': 'application/json' } });
    }

    // 그 외 일반 요청은 원본 fetch 시도 후 에러 시 Safe Fallback
    try {
      const resp = await origFetch.apply(this, arguments);
      if (!resp.ok && resp.status === 404) {
        return new Response(JSON.stringify({ ok: true, demo: true }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      }
      return resp;
    } catch (err) {
      console.log('GitHub Pages Fetch Fallback for:', url);
      return new Response(JSON.stringify({ ok: true, demo: true }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  };
})();
