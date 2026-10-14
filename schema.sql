-- PulseTrade — watchlist table + Row Level Security policies.
-- Run this once in the Supabase dashboard: SQL Editor -> New query -> paste -> Run.

create table if not exists public.watchlist (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    ticker text not null,
    created_at timestamptz not null default now(),
    unique (user_id, ticker)
);

alter table public.watchlist enable row level security;

-- Each user can only see, add, and remove their own watchlist rows.
create policy "Users can view their own watchlist"
    on public.watchlist for select
    using (auth.uid() = user_id);

create policy "Users can add to their own watchlist"
    on public.watchlist for insert
    with check (auth.uid() = user_id);

create policy "Users can remove from their own watchlist"
    on public.watchlist for delete
    using (auth.uid() = user_id);
