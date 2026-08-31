<script>
  import { page } from '$app/stores';
  import PostEditor from '$lib/components/PostEditor.svelte';
</script>

<PostEditor postId={$page.params.id} />
