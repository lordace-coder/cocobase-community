<script lang="ts">
	import '../app.css';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { auth, toast } from '$lib/stores';
	import { onMount } from 'svelte';

	const isPublic = (path: string) => path === `${base}/login` || path === `${base}/login/`;

	onMount(() => {
		if (!$auth.token && !isPublic($page.url.pathname)) {
			goto(`${base}/login`);
		}
	});

	const navItems = [
		{ href: `${base}/`, label: 'Overview', icon: '⬡' },
		{ href: `${base}/projects`, label: 'Projects', icon: '◧' },
		{ href: `${base}/users`, label: 'Users', icon: '◎' },
		{ href: `${base}/health`, label: 'Health', icon: '◈' }
	];

	function logout() {
		auth.logout();
		goto(`${base}/login`);
	}

	$: showLayout = $auth.token && !isPublic($page.url.pathname);
	$: currentPath = $page.url.pathname;
</script>

{#if $toast}
	<div
		class="fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-sm font-medium transition-all
           {$toast.type === 'success' ? 'bg-green-700 text-green-100' :
            $toast.type === 'error' ? 'bg-red-700 text-red-100' : 'bg-coco-700 text-coco-100'}"
	>
		{$toast.message}
	</div>
{/if}

{#if !showLayout}
	<slot />
{:else}
	<div class="flex h-screen overflow-hidden bg-gray-950">
		<!-- Sidebar -->
		<aside class="w-60 flex flex-col bg-gray-900 border-r border-gray-800 flex-shrink-0">
			<!-- Logo -->
			<div class="h-14 flex items-center px-5 border-b border-gray-800">
				<span class="text-coco-400 font-bold text-lg tracking-tight">Coco</span>
				<span class="text-white font-bold text-lg">Base</span>
				<span class="ml-2 badge badge-blue text-[10px]">dashboard</span>
			</div>

			<!-- Nav -->
			<nav class="flex-1 overflow-y-auto px-3 py-4 space-y-0.5">
				{#each navItems as item}
					<a
						href={item.href}
						class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors
                           {currentPath === item.href || (item.href !== `${base}/` && currentPath.startsWith(item.href))
							? 'bg-coco-600/20 text-coco-300'
							: 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'}"
					>
						<span class="text-base">{item.icon}</span>
						{item.label}
					</a>
				{/each}
			</nav>

			<!-- User -->
			<div class="border-t border-gray-800 p-3">
				{#if $auth.user}
					<div class="flex items-center gap-3 px-2 py-2">
						<div
							class="w-8 h-8 rounded-full bg-coco-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
						>
							{($auth.user.username ?? $auth.user.email ?? '?')[0].toUpperCase()}
						</div>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-gray-200 truncate">
								{$auth.user.username ?? 'Admin'}
							</div>
							<div class="text-xs text-gray-500 truncate">{$auth.user.email}</div>
						</div>
					</div>
				{/if}
				<button on:click={logout} class="btn btn-ghost w-full justify-start mt-1 text-xs">
					⎋ &nbsp;Sign out
				</button>
			</div>
		</aside>

		<!-- Main -->
		<main class="flex-1 overflow-y-auto">
			<slot />
		</main>
	</div>
{/if}
