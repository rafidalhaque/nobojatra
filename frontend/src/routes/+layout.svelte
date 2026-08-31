<script>
  import '../app.css';
  import { onMount } from 'svelte';
  import { lang, initLangFromBrowser } from '$lib/i18n';
  import { session } from '$lib/stores.js';
  import { applyTheme, osTheme } from '$lib/theme.js';

  let { children } = $props();

  onMount(() => {
    // drop the pre-boot shell painted by app.html
    document.getElementById('shell-mast')?.remove();
    document.getElementById('shell-wait')?.remove();

    initLangFromBrowser();

    // Follow the OS theme until a profile preference loads. Once signed in the
    // DB value wins and this listener stops mattering.
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => {
      const me = $session;
      if (!me) applyTheme(osTheme());
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  });

  // keep <html lang> in sync so the right font family applies
  $effect(() => {
    if (typeof document !== 'undefined') document.documentElement.lang = $lang;
  });
</script>

{@render children()}
