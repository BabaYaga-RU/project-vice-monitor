/* Editable S-800 background for the Skylet Assistant page. */
import * as THREE from './vendor/three/three.module.js';
import { GLTFLoader } from './vendor/three/GLTFLoader.js';
import { DRACOLoader } from './vendor/three/DRACOLoader.js';

const host = document.querySelector('[data-s800-background]');

if (host) {
  const base = new URL('.', import.meta.url);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 1, 0.01, 100);
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
  const loader = new GLTFLoader();
  const draco = new DRACOLoader().setDecoderPath(new URL('./vendor/three/draco/', base).href);
  let character = null;
  let targetX = 0;
  let targetY = 0;
  let currentX = 0;
  let currentY = 0;

  loader.setDRACOLoader(draco);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.35;
  host.appendChild(renderer.domElement);
  scene.add(new THREE.HemisphereLight('#dbe8d8', '#0a100d', 3.2));
  const key = new THREE.DirectionalLight('#e6f5dd', 4.1);
  key.position.set(2, 4, 4);
  scene.add(key);
  const rim = new THREE.PointLight('#a8ffb7', 9, 8);
  rim.position.set(-3, 2, -2);
  scene.add(rim);

  function resize() {
    const width = Math.max(1, host.clientWidth);
    const height = Math.max(1, host.clientHeight);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
  }

  function frame(root) {
    const head = root.getObjectByName('S800Endo-Head') || root;
    const box = new THREE.Box3().setFromObject(head);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    center.y += size.y * 0.05;
    const distance = size.y / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.72);
    camera.position.set(center.x, center.y, center.z + distance);
    camera.lookAt(center);
  }

  async function load() {
    try {
      character = (await loader.loadAsync(new URL('./S-800-bust.glb', base).href)).scene;
      scene.add(character);
      resize();
      frame(character);
      host.dataset.s800Ready = 'true';
    } catch (error) {
      console.error('S-800 background failed to load: ' + (error?.message || error));
      host.dataset.s800Ready = 'false';
    }
  }

  function draw() {
    requestAnimationFrame(draw);
    if (character) {
      currentX += (targetX - currentX) * 0.05;
      currentY += (targetY - currentY) * 0.05;
      character.rotation.y = currentX * 0.13;
      character.rotation.x = -currentY * 0.045;
    }
    renderer.render(scene, camera);
  }

  document.addEventListener('pointermove', (event) => {
    targetX = (event.clientX / window.innerWidth - .5) * 2;
    targetY = (event.clientY / window.innerHeight - .5) * 2;
  }, { passive: true });
  new ResizeObserver(resize).observe(host);
  load();
  draw();
  window.S800Background = {
    reveal() { document.body.classList.add('is-s800-revealed'); },
    hide() { document.body.classList.remove('is-s800-revealed'); }
  };
}
