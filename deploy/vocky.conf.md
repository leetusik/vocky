# vocky.conf — moved out of this repo (2026-08-04)

`deploy/vocky.conf` no longer lives here. It was **moved to the edge repo** by that repo's
phase **P6.S2** on 2026-08-04, so the vhost has one file and one owner and cannot drift.

## Canonical home

- **File:** `edge/conf.d/vocky.conf`
- **Repo:** the edge repo — locally `/Users/sugang/projects/personal/edge`,
  remote `https://github.com/leetusik/edge.git`

## How it reaches the box

Through the edge repo's own path only:

    ./validate.sh   # dummy certs + compose config + throwaway-container nginx -t over the whole conf.d/ tree
    ./stage.sh      # rsync the tree to the VM (never --delete)
    ./deploy.sh     # nginx -t inside the running edge-nginx container, then a graceful nginx -s reload

(or the edge repo's GitHub Actions deploy workflow, which wraps that same loop). It lands at
`/home/opc/edge/conf.d/vocky.conf` on the box.

## Rules

- **Do not recreate a copy of the conf here.** Two copies is exactly the drift this move removed.
- Edit the vhost in the edge repo and apply it there; never `scp` it by hand and never edit the
  box copy directly.
- vocky's `P12.S4` bring-up deploys through that path instead of its old manual `scp` procedure.
