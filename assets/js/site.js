(() => {
  const root = document.documentElement;
  root.classList.add('js');

  const menuButton = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#primary-navigation');
  if (menuButton && navigation) {
    const closeMenu = () => {
      menuButton.setAttribute('aria-expanded', 'false');
      menuButton.setAttribute('aria-label', 'Open navigation');
      navigation.classList.remove('is-open');
    };
    menuButton.addEventListener('click', () => {
      const opening = menuButton.getAttribute('aria-expanded') !== 'true';
      menuButton.setAttribute('aria-expanded', String(opening));
      menuButton.setAttribute('aria-label', opening ? 'Close navigation' : 'Open navigation');
      navigation.classList.toggle('is-open', opening);
    });
    navigation.addEventListener('click', event => {
      if (event.target.closest('a')) closeMenu();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') closeMenu();
    });
    window.addEventListener('resize', () => {
      if (window.matchMedia('(min-width: 981px)').matches) closeMenu();
    });
  }

  const heroVideo = document.querySelector('.hero__video');
  const videoToggle = document.querySelector('.video-toggle');
  const audioToggle = document.querySelector('.audio-toggle');
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const mobileViewport = window.matchMedia('(max-width: 760px)');
  if (heroVideo && videoToggle) {
    const syncVideoControl = () => {
      const paused = heroVideo.paused;
      videoToggle.setAttribute('aria-pressed', String(paused));
      videoToggle.setAttribute('aria-label', paused ? 'Play hero video' : 'Pause hero video');
    };
    const syncAudioControl = () => {
      if (!audioToggle) return;
      const soundOn = !heroVideo.muted;
      audioToggle.setAttribute('aria-pressed', String(soundOn));
      audioToggle.setAttribute('aria-label', soundOn ? 'Mute hero video sound' : 'Enable hero video sound');
      const label = audioToggle.querySelector('.audio-toggle__label');
      if (label) label.textContent = soundOn ? 'Sound on' : 'Sound off';
    };
    const chooseHeroAsset = () => {
      const mobile = mobileViewport.matches;
      const source = mobile ? heroVideo.dataset.mobileSrc : heroVideo.dataset.desktopSrc;
      const poster = mobile ? heroVideo.dataset.mobilePoster : heroVideo.dataset.desktopPoster;
      if (source && heroVideo.dataset.activeSource !== source) {
        heroVideo.pause();
        heroVideo.dataset.activeSource = source;
        heroVideo.poster = poster;
        heroVideo.src = source;
        heroVideo.load();
      }
    };
    const applyMotionPreference = () => {
      chooseHeroAsset();
      if (reducedMotion.matches) {
        heroVideo.pause();
        videoToggle.hidden = true;
        if (audioToggle) audioToggle.hidden = true;
      } else {
        videoToggle.hidden = false;
        if (audioToggle) audioToggle.hidden = false;
        heroVideo.play().catch(() => syncVideoControl());
      }
      syncVideoControl();
      syncAudioControl();
    };
    videoToggle.addEventListener('click', () => {
      if (heroVideo.paused) heroVideo.play().catch(syncVideoControl);
      else heroVideo.pause();
    });
    audioToggle?.addEventListener('click', () => {
      heroVideo.muted = !heroVideo.muted;
      if (!heroVideo.muted && heroVideo.paused) {
        heroVideo.play().catch(() => { heroVideo.muted = true; syncAudioControl(); });
      }
      syncAudioControl();
    });
    heroVideo.addEventListener('play', syncVideoControl);
    heroVideo.addEventListener('pause', syncVideoControl);
    heroVideo.addEventListener('volumechange', syncAudioControl);
    reducedMotion.addEventListener?.('change', applyMotionPreference);
    mobileViewport.addEventListener?.('change', applyMotionPreference);
    applyMotionPreference();
  }

  if (!reducedMotion.matches && 'IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -30px 0px' });
    document.querySelectorAll('[data-reveal]').forEach(element => revealObserver.observe(element));
  } else {
    document.querySelectorAll('[data-reveal]').forEach(element => element.classList.add('is-visible'));
  }

  const form = document.querySelector('.enquiry-form');
  if (form) {
    const status = form.querySelector('.form-status');
    const tokenField = form.querySelector('[name="csrf_token"]');
    const showStatus = (message, includeEmail = false) => {
      if (!status) return;
      status.replaceChildren(document.createTextNode(message));
      if (includeEmail) {
        status.append(document.createTextNode(' '));
        const link = document.createElement('a');
        link.href = 'mailto:info@thebioniceye.co.uk';
        link.textContent = 'info@thebioniceye.co.uk';
        status.append(link, document.createTextNode('.'));
      }
    };

    const query = new URLSearchParams(window.location.search).get('enquiry');
    if (query === 'sent') showStatus('Thank you. Your enquiry has been sent.');
    if (query === 'failed') showStatus('We could not send your enquiry just now. Please email', true);

    form.addEventListener('submit', async event => {
      if (!form.reportValidity()) return;
      event.preventDefault();
      const token = tokenField?.value || '';
      if (!/^[a-f0-9]{64}$/i.test(token)) {
        showStatus('The server-side form is not available in this static preview. Please email', true);
        return;
      }
      const button = form.querySelector('button[type="submit"]');
      if (button) button.disabled = true;
      showStatus('Sending…');
      try {
        const response = await fetch(form.action, {
          method: 'POST',
          body: new FormData(form),
          credentials: 'same-origin',
          headers: { Accept: 'application/json' },
        });
        const payload = await response.json();
        showStatus(payload.message || (response.ok ? 'Thank you.' : 'Please check the form and try again.'), !response.ok);
        if (response.ok && payload.ok) form.reset();
      } catch (_error) {
        showStatus('We could not reach the enquiry service. Please email', true);
      } finally {
        if (button) button.disabled = false;
      }
    });
  }
})();
