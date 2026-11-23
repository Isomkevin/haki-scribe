-- Link HakiScribe matters to canonical HakiChain workspaces (contract 2026-11).

ALTER TABLE public.haki_matters
  ADD COLUMN IF NOT EXISTS hakichain_client_id text,
  ADD COLUMN IF NOT EXISTS hakichain_workspace_id text,
  ADD COLUMN IF NOT EXISTS hakichain_linked_at timestamptz;

CREATE INDEX IF NOT EXISTS haki_matters_hakichain_workspace_idx
  ON public.haki_matters (hakichain_workspace_id)
  WHERE hakichain_workspace_id IS NOT NULL;

COMMENT ON COLUMN public.haki_matters.hakichain_client_id IS
  'HakiChain workspaces.client_id used in /workspace?ws= URLs';
COMMENT ON COLUMN public.haki_matters.hakichain_workspace_id IS
  'HakiChain workspaces.id (uuid as text)';
