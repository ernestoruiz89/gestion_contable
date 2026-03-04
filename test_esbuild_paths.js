const path = require("path");
const fs = require("fs");

// Mocking Frappe's path resolution
const bench_path = path.resolve(__dirname, "../../..");
const apps_path = path.resolve(bench_path, "apps");
const sites_path = path.resolve(bench_path, "sites");

console.log("Expected bench_path:", bench_path);
console.log("Expected apps_path:", apps_path);

let app_list = ["gestion_contable"]; // Simplified list

const public_paths = app_list.reduce((out, app) => {
    // Frappe 15 esbuild utils.js logic:
    out[app] = path.resolve(apps_path, app, app, "public");
    return out;
}, {});

console.log("Resolved public paths object:", public_paths);
console.log("get_public_path('gestion_contable') normally returns:", public_paths['gestion_contable']);

// This is where it crashes:
let public_path = public_paths['gestion_contable'];
console.log("Trying to resolve path using public_path:");
try {
    let resolved = path.resolve(public_path, "**", "*.bundle.{js,ts,css,sass,scss,less,styl,jsx}");
    console.log("Resolved OK:", resolved);
} catch (e) {
    console.error("ERROR when calling path.resolve:", e.message);
}
