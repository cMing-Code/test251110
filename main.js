import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.159/build/three.module.js";

const sceneRoot = document.getElementById("scene-root");
const videoElement = document.getElementById("input-video");
const radiusLabel = document.getElementById("radius-label");
const rightHandLabel = document.getElementById("right-hand-label");

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
sceneRoot.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x04060f, 0.0075);

const camera = new THREE.PerspectiveCamera(
  55,
  window.innerWidth / window.innerHeight,
  0.1,
  1000
);
camera.position.set(0, 0, 120);

const hemi = new THREE.HemisphereLight(0x6df1ff, 0x060612, 0.8);
scene.add(hemi);

const PARTICLE_COUNT = 6500;
const positions = new Float32Array(PARTICLE_COUNT * 3);
const basePositions = new Float32Array(PARTICLE_COUNT * 3);
const directions = new Float32Array(PARTICLE_COUNT * 3);
const radialNoise = new Float32Array(PARTICLE_COUNT);

for (let i = 0; i < PARTICLE_COUNT; i++) {
  const idx = i * 3;
  const radius = THREE.MathUtils.randFloat(10, 60);
  const theta = THREE.MathUtils.randFloat(0, Math.PI * 2);
  const phi = THREE.MathUtils.randFloat(0, Math.PI);
  const x = radius * Math.sin(phi) * Math.cos(theta);
  const y = radius * Math.sin(phi) * Math.sin(theta);
  const z = radius * Math.cos(phi);
  positions[idx] = basePositions[idx] = x;
  positions[idx + 1] = basePositions[idx + 1] = y;
  positions[idx + 2] = basePositions[idx + 2] = z;

  const length = Math.max(Math.hypot(x, y, z), 0.0001);
  directions[idx] = x / length;
  directions[idx + 1] = y / length;
  directions[idx + 2] = z / length;
  radialNoise[i] = THREE.MathUtils.randFloat(-6, 6);
}

const geometry = new THREE.BufferGeometry();
geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));

const material = new THREE.PointsMaterial({
  color: 0x72ffe6,
  size: 1.6,
  transparent: true,
  opacity: 0.9,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});

const particleSystem = new THREE.Points(geometry, material);
scene.add(particleSystem);

const planetState = {
  radius: 55,
  targetRadius: 55,
  baseRadius: 55,
};
radiusLabel.textContent = planetState.radius.toFixed(0);

const rightHandState = {
  openness: 0.5,
  targetOpenness: 0.5,
  label: "等待",
  position: new THREE.Vector3(0, 0, 60),
  active: false,
};

let spreadFactor = 1;
let contractionFactor = 1;
let globalTime = 0;

function updateRightHandState(landmarks) {
  const wrist = landmarks[0];
  const tips = [4, 8, 12, 16, 20];
  let sum = 0;
  tips.forEach((idx) => {
    const tip = landmarks[idx];
    const dx = tip.x - wrist.x;
    const dy = tip.y - wrist.y;
    const dz = tip.z - wrist.z;
    sum += Math.sqrt(dx * dx + dy * dy + dz * dz);
  });

  rightHandState.targetOpenness = sum / tips.length;
  rightHandState.openness = THREE.MathUtils.lerp(
    rightHandState.openness,
    rightHandState.targetOpenness,
    0.2
  );

  if (rightHandState.openness < 0.075) {
    rightHandState.label = "握拳·星球收缩";
    contractionFactor = THREE.MathUtils.lerp(contractionFactor, 0.5, 0.05);
  } else if (rightHandState.openness > 0.12) {
    rightHandState.label = "张开·星球扩张";
    contractionFactor = THREE.MathUtils.lerp(contractionFactor, 1.6, 0.05);
  } else {
    rightHandState.label = "自然";
    contractionFactor = THREE.MathUtils.lerp(contractionFactor, 1, 0.05);
  }

  const opennessNormalized = THREE.MathUtils.clamp(
    (rightHandState.openness - 0.04) / 0.16,
    0,
    1
  );
  planetState.targetRadius = THREE.MathUtils.lerp(35, 95, opennessNormalized);

  const worldX = (wrist.x - 0.5) * 160;
  const worldY = -(wrist.y - 0.5) * 100;
  const worldZ = THREE.MathUtils.clamp(-wrist.z * 150, -40, 40);

  rightHandState.position.lerp(new THREE.Vector3(worldX, worldY, worldZ), 0.35);
  rightHandState.active = true;
  rightHandLabel.textContent = rightHandState.label;
  radiusLabel.textContent = planetState.radius.toFixed(0);
}

function animate() {
  requestAnimationFrame(animate);
  globalTime += 0.005;

  planetState.radius = THREE.MathUtils.lerp(
    planetState.radius,
    planetState.targetRadius,
    0.08
  );
  spreadFactor = THREE.MathUtils.lerp(spreadFactor, contractionFactor, 0.05);

  const positionsAttr = geometry.attributes.position;
  const arr = positionsAttr.array;
  const noiseAmp = 3 + spreadFactor * 0.5;

  const influenceRadius = 28;

  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const idx = i * 3;
    const dirX = directions[idx];
    const dirY = directions[idx + 1];
    const dirZ = directions[idx + 2];
    const desiredRadius = (planetState.radius + radialNoise[i]) * spreadFactor;
    const targetX = dirX * desiredRadius;
    const targetY = dirY * desiredRadius;
    const targetZ = dirZ * desiredRadius * 0.9;

    let px = arr[idx];
    let py = arr[idx + 1];
    let pz = arr[idx + 2];

    const noise =
      Math.sin(globalTime * 5 + i * 0.3) * 0.4 +
      Math.cos(globalTime * 3 + i * 0.1) * 0.3;

    px += (targetX - px) * 0.07 + noise * noiseAmp * 0.01;
    py += (targetY - py) * 0.07 + noise * noiseAmp * 0.008;
    pz += (targetZ - pz) * 0.08 + noise * 0.15;

    if (rightHandState.active) {
      const dx = px - rightHandState.position.x;
      const dy = py - rightHandState.position.y;
      const dz = pz - rightHandState.position.z;
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);

      if (dist < influenceRadius) {
        const force = (1 - dist / influenceRadius) * (rightHandState.openness + 0.3);
        px += (dx / dist) * force * 6;
        py += (dy / dist) * force * 6;
        pz += (dz / dist) * force * 3;
      }
    }

    arr[idx] = px;
    arr[idx + 1] = py;
    arr[idx + 2] = pz;
  }

  positionsAttr.needsUpdate = true;
  particleSystem.rotation.y += 0.0006;
  renderer.render(scene, camera);
}

animate();

function onResults(results) {
  rightHandState.active = false;
  rightHandLabel.textContent = "等待";
  planetState.targetRadius = THREE.MathUtils.lerp(
    planetState.targetRadius,
    planetState.baseRadius,
    0.02
  );
  radiusLabel.textContent = planetState.radius.toFixed(0);

  if (!results.multiHandLandmarks) return;

  results.multiHandLandmarks.forEach((landmarks, idx) => {
    const handedness = results.multiHandedness[idx].label;
    if (handedness === "Right") updateRightHandState(landmarks);
  });
}

const hands = new Hands({
  locateFile: (file) =>
    `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
});

hands.setOptions({
  maxNumHands: 2,
  modelComplexity: 1,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.5,
});

hands.onResults(onResults);

const cameraFeed = new Camera(videoElement, {
  onFrame: async () => {
    await hands.send({ image: videoElement });
  },
  width: 1280,
  height: 720,
});
cameraFeed.start();

window.addEventListener("resize", () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});
