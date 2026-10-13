# target dev      : Vite dev server dengan hot reload (src di-mount)
# target produksi : build statis dilayani nginx
FROM node:22-alpine AS dasar
WORKDIR /app
COPY package.json package-lock.json* ./
RUN if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
COPY . .
# Aset PDF.js (cmap & font standar) dibundel lokal — tidak ada CDN saat runtime (B1)
RUN mkdir -p public/pdfjs && cp -r node_modules/pdfjs-dist/cmaps node_modules/pdfjs-dist/standard_fonts public/pdfjs/

FROM dasar AS dev
ENV API_URL=http://api:8000
EXPOSE 8080
CMD ["npm", "run", "dev"]

FROM dasar AS bangun
RUN npm run build && node scripts/cek-offline.mjs dist

FROM nginx:1.27-alpine AS produksi
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=bangun /app/dist /usr/share/nginx/html
