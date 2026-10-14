# Campus Customs Desk (frontend)

React + Vite + TypeScript dashboard for the Campus Customs agent team.

```bash
npm install
npm run dev
```

`npm run dev` opens http://localhost:5173. The page calls the FastAPI backend at http://localhost:8000; start that first from `backend/` with `uvicorn main:app --reload --port 8000`. To point at a different backend, set `VITE_API_BASE`.

See `../output/design.md` for the layout and design choices.
