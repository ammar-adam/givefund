/**
 * GiveFund 3D hero — self-contained Three.js particle field.
 * Mouse-reactive gradient point cloud layered into the dark hero.
 * Fails gracefully: if WebGL/CDN/module load fails or reduced-motion
 * is requested, it does nothing and the CSS aurora hero remains.
 */
const REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function hasWebGL() {
  try {
    const c = document.createElement("canvas");
    return !!(
      window.WebGLRenderingContext &&
      (c.getContext("webgl") || c.getContext("experimental-webgl"))
    );
  } catch {
    return false;
  }
}

async function initHero3D() {
  if (REDUCED || !hasWebGL()) return;
  const hero = document.querySelector(".hero");
  if (!hero) return;

  let THREE;
  try {
    THREE = await import("https://unpkg.com/three@0.160.0/build/three.module.js");
  } catch {
    return; // CDN/module failed — aurora fallback stays
  }

  const canvas = document.createElement("canvas");
  canvas.className = "hero-3d-canvas";
  canvas.setAttribute("aria-hidden", "true");
  hero.appendChild(canvas);

  const renderer = new THREE.WebGLRenderer({
    canvas,
    alpha: true,
    antialias: true,
    powerPreference: "high-performance",
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, 1, 0.1, 100);
  camera.position.z = 13;

  // Build a noisy spherical shell of points with a gradient color ramp.
  const COUNT = 2600;
  const positions = new Float32Array(COUNT * 3);
  const colors = new Float32Array(COUNT * 3);

  const cA = new THREE.Color(0xff5a3c); // coral
  const cB = new THREE.Color(0xffb23e); // amber
  const cC = new THREE.Color(0x7c5cff); // violet

  for (let i = 0; i < COUNT; i++) {
    const t = Math.acos(2 * Math.random() - 1);
    const p = 2 * Math.PI * Math.random();
    const r = 6.4 + (Math.random() - 0.5) * 1.6;
    const x = r * Math.sin(t) * Math.cos(p);
    const y = r * Math.cos(t);
    const z = r * Math.sin(t) * Math.sin(p);
    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    const ny = (y / r + 1) / 2; // 0..1
    const col = new THREE.Color();
    if (ny < 0.5) col.copy(cA).lerp(cB, ny * 2);
    else col.copy(cB).lerp(cC, (ny - 0.5) * 2);
    colors[i * 3] = col.r;
    colors[i * 3 + 1] = col.g;
    colors[i * 3 + 2] = col.b;
  }

  const geo = new THREE.BufferGeometry();
  geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));

  const mat = new THREE.PointsMaterial({
    size: 0.085,
    vertexColors: true,
    transparent: true,
    opacity: 0.95,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    sizeAttenuation: true,
  });

  const points = new THREE.Points(geo, mat);
  const group = new THREE.Group();
  group.add(points);

  // Inner faint core for depth.
  const coreGeo = new THREE.IcosahedronGeometry(4.1, 1);
  const coreMat = new THREE.MeshBasicMaterial({
    color: 0xff7a4a,
    wireframe: true,
    transparent: true,
    opacity: 0.07,
  });
  group.add(new THREE.Mesh(coreGeo, coreMat));
  scene.add(group);

  let targetX = 0;
  let targetY = 0;
  window.addEventListener(
    "mousemove",
    (e) => {
      targetX = (e.clientX / window.innerWidth - 0.5) * 0.6;
      targetY = (e.clientY / window.innerHeight - 0.5) * 0.4;
    },
    { passive: true }
  );

  function resize() {
    const w = hero.clientWidth;
    const h = hero.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  resize();
  window.addEventListener("resize", resize, { passive: true });

  // Fade in once first frame is drawn.
  requestAnimationFrame(() => canvas.classList.add("ready"));

  let raf;
  let running = true;
  const clock = new THREE.Clock();

  function animate() {
    if (!running) return;
    raf = requestAnimationFrame(animate);
    const dt = clock.getDelta();
    group.rotation.y += dt * 0.12;
    group.rotation.x += (targetY - group.rotation.x) * 0.04;
    group.rotation.y += (targetX - (group.rotation.y % (Math.PI * 2))) * 0.0;
    group.position.x += (targetX * 1.4 - group.position.x) * 0.05;
    group.position.y += (-targetY * 1.2 - group.position.y) * 0.05;
    renderer.render(scene, camera);
  }
  animate();

  // Pause when hero off-screen to save battery/CPU.
  const io = new IntersectionObserver(
    (entries) => {
      const visible = entries[0].isIntersecting;
      if (visible && !running) {
        running = true;
        animate();
      } else if (!visible) {
        running = false;
        cancelAnimationFrame(raf);
      }
    },
    { threshold: 0.01 }
  );
  io.observe(hero);
}

initHero3D();
