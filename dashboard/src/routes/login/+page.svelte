<script lang="ts">
	import { goto } from '$app/navigation';
	import { base } from '$app/paths';
	import { authApi } from '$lib/api';
	import { auth, showToast } from '$lib/stores';
	import { onMount } from 'svelte';

	let email = '';
	let password = '';
	let loading = false;
	let error = '';

	onMount(() => {
		if ($auth.token) goto(`${base}/`);
	});

	async function login() {
		if (!email || !password) {
			error = 'Email and password are required.';
			return;
		}
		loading = true;
		error = '';
		try {
			const res = await authApi.login(email, password);
			// Decode user info from JWT (payload is base64url encoded)
			const parts = res.access_token.split('.');
			let userInfo = { username: email.split('@')[0], email, id: '' };
			if (parts.length === 3) {
				try {
					const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/')));
					userInfo = {
						username: payload.user ?? userInfo.username,
						email,
						id: payload.userId ?? ''
					};
				} catch {}
			}
			auth.login(res.access_token, userInfo);
			showToast('Welcome back!', 'success');
			goto(`${base}/`);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Login failed';
		} finally {
			loading = false;
		}
	}
</script>

<svelte:head>
	<title>Login — CocoBase Dashboard</title>
</svelte:head>

<div class="min-h-screen bg-gray-950 flex items-center justify-center p-4">
	<div class="w-full max-w-sm">
		<!-- Logo -->
		<div class="text-center mb-8">
			<div class="inline-flex items-center gap-1 mb-2">
				<span class="text-coco-400 font-bold text-3xl">Coco</span>
				<span class="text-white font-bold text-3xl">Base</span>
			</div>
			<p class="text-gray-500 text-sm">Sign in to your dashboard</p>
		</div>

		<form
			on:submit|preventDefault={login}
			class="bg-gray-900 border border-gray-800 rounded-2xl p-8 shadow-2xl space-y-5"
		>
			<div>
				<label class="label" for="email">Email</label>
				<input
					id="email"
					type="email"
					bind:value={email}
					class="input"
					placeholder="admin@example.com"
					autocomplete="email"
					disabled={loading}
				/>
			</div>

			<div>
				<label class="label" for="password">Password</label>
				<input
					id="password"
					type="password"
					bind:value={password}
					class="input"
					placeholder="••••••••"
					autocomplete="current-password"
					disabled={loading}
				/>
			</div>

			{#if error}
				<p class="text-red-400 text-sm bg-red-900/30 border border-red-800 rounded-lg px-3 py-2">
					{error}
				</p>
			{/if}

			<button type="submit" class="btn btn-primary w-full justify-center py-2.5" disabled={loading}>
				{#if loading}
					<span class="animate-spin text-base">◌</span> Signing in…
				{:else}
					Sign in
				{/if}
			</button>
		</form>

		<p class="text-center text-gray-600 text-xs mt-6">
			CocoBase v1.5 · <a href="/docs" class="hover:text-gray-400 transition-colors">API docs</a>
		</p>
	</div>
</div>
