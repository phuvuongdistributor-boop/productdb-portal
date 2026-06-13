# ProductDB V2 Production Deployment

## Production architecture

- Deploy the included `Dockerfile` to a managed container host or Linux VPS.
- Attach a persistent volume at `/app/runtime`.
- Put the service behind an HTTPS domain.
- Do not expose port `8501` directly from the office Windows computer.

## Render Blueprint

The repository includes `render.yaml` configured for a free Docker trial in Render's
Singapore region. Runtime files are stored under `/tmp/productdb-runtime` and can be
deleted whenever the free service restarts or redeploys. Use this mode only to test the
Portal. Production requires a paid service with a persistent disk mounted at `/app/runtime`.

After the code is in GitHub:

1. Open Render Dashboard and choose **New > Blueprint**.
2. Connect the repository containing this `render.yaml`.
3. Enter `PRODUCTDB_ADMIN_PASSWORD` and `GOOGLE_SERVICE_ACCOUNT_JSON` when prompted.
4. Create the Blueprint and wait for `/_stcore/health` to report healthy.

Render supplies `RENDER_EXTERNAL_URL` automatically. ProductDB uses it for customer
catalog links unless `PRODUCTDB_PUBLIC_URL` is set to a custom HTTPS domain.

## Environment variables

Copy the names from `deploy/.env.example` into the hosting platform's secret manager.
Never commit the Google service-account JSON or the production admin password.

Share the LIVE Google Sheet with the service-account email as Viewer. The Portal uses
the read-only Sheets scope. In trial mode, quotations, users, and leads are temporary.

## Deployment checks

1. Open `https://your-domain/_stcore/health`; it must return `ok`.
2. Log in as admin and immediately change the bootstrap password.
3. Create a real sale account and disable `sale.demo` if it was migrated.
4. Confirm a sale cannot open `/dashboard` or `/users`.
5. Confirm `/catalog` opens without login and contains no prices.
6. Before production, add persistent storage and confirm users, leads, and quotations
   survive a container restart.

## URLs

- Staff Portal: `https://your-domain/`
- Customer catalog: `https://your-domain/catalog`
- Customer product: `https://your-domain/catalog?code=PRODUCT_CODE`

Set `PRODUCTDB_PUBLIC_URL=https://your-domain` only after adding a custom domain.
