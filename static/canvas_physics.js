/**
 * Resilient Pocket - Real Physics & Mathematics Canvas Background Animation
 * 
 * Mathematical & Physical Systems Implemented:
 * 1. Harmonic Sine/Cosine Wave Oscillations: Y(x, t) = A * sin(k*x - w*t) + B * cos(2*k*x + w*t)
 * 2. Gravitational / Magnetic Spring Particle Attraction: F_grav = (G * m1 * m2) / (r^2 + eps)
 * 3. Euler Integration Motion: Velocity & Position updates with Damping Friction (v = v * 0.96)
 * 4. Reactive Health FSM Color States: Dynamic vector palette based on financial health state.
 */

class MathPhysicsBackground {
  constructor(canvasId = "bg-canvas") {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) return;
    this.ctx = this.canvas.getContext("2d");

    this.particles = [];
    this.numParticles = 65;
    this.time = 0;
    this.mouse = { x: -1000, y: -1000, active: false };

    // Default Theme Color RGB (Emerald Teal)
    this.themeColor = { r: 56, g: 189, b: 248 }; // Cyan #38bdf8

    this.init();
    this.bindEvents();
    this.animate();
  }

  init() {
    this.resize();
    this.particles = [];

    // Create particles with random mass, position, and initial momentum velocity
    for (let i = 0; i < this.numParticles; i++) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: Math.random() * this.canvas.height,
        vx: (Math.random() - 0.5) * 1.2,
        vy: (Math.random() - 0.5) * 1.2,
        radius: Math.random() * 2.5 + 1.2,
        mass: Math.random() * 2 + 1,
        phase: Math.random() * Math.PI * 2
      });
    }
  }

  resize() {
    this.canvas.width = window.innerWidth;
    this.canvas.height = window.innerHeight;
  }

  bindEvents() {
    window.addEventListener("resize", () => this.resize());
    window.addEventListener("mousemove", (e) => {
      this.mouse.x = e.clientX;
      this.mouse.y = e.clientY;
      this.mouse.active = true;
    });
    window.addEventListener("mouseleave", () => {
      this.mouse.active = false;
    });
  }

  setThemeFromHealth(healthState) {
    if (!healthState) return;
    if (healthState.includes("Thriving")) {
      this.themeColor = { r: 16, g: 185, b: 129 }; // Emerald Green
    } else if (healthState.includes("Steady")) {
      this.themeColor = { r: 20, g: 184, b: 166 }; // Teal
    } else if (healthState.includes("Drooping")) {
      this.themeColor = { r: 245, g: 158, b: 11 }; // Amber
    } else if (healthState.includes("Critical")) {
      this.themeColor = { r: 239, g: 68, b: 68 }; // Crimson Red
    }
  }

  // 1. Render Harmonic Wave Field (Mathematical Sine/Cosine Fourier Approximation)
  drawHarmonicWaves() {
    const ctx = this.ctx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    ctx.save();
    ctx.lineWidth = 1.5;

    // Draw 3 superimposed wave harmonics
    for (let waveIdx = 0; waveIdx < 3; waveIdx++) {
      ctx.beginPath();
      
      const alpha = 0.08 - waveIdx * 0.02;
      ctx.strokeStyle = `rgba(${this.themeColor.r}, ${this.themeColor.g}, ${this.themeColor.b}, ${alpha})`;

      const amplitude = 35 + waveIdx * 15;
      const frequency = 0.003 + waveIdx * 0.001;
      const speed = this.time * (0.015 + waveIdx * 0.005);
      const yOffset = h * 0.45 + waveIdx * 60;

      for (let x = 0; x <= w; x += 15) {
        // Compound Sine & Cosine Physics Equation: Y = A*sin(k*x - w*t) + B*cos(2k*x + w*t)
        const y = yOffset + Math.sin(x * frequency - speed) * amplitude + Math.cos(x * frequency * 2.2 + speed * 1.5) * (amplitude * 0.4);
        
        if (x === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.stroke();
    }
    ctx.restore();
  }

  // 2. Physics Particle Simulation: Gravitational Attraction & Friction Damping (Euler Integration)
  updatePhysics() {
    const w = this.canvas.width;
    const h = this.canvas.height;
    const G = 150.0; // Attraction constant
    const damping = 0.98; // Friction factor

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];

      // Oscillatory floating acceleration
      p.phase += 0.02;
      const waveAx = Math.cos(p.phase) * 0.03;
      const waveAy = Math.sin(p.phase) * 0.03;

      p.vx += waveAx;
      p.vy += waveAy;

      // Mouse Gravitational Spring Attraction
      if (this.mouse.active) {
        const dx = this.mouse.x - p.x;
        const dy = this.mouse.y - p.y;
        const distSq = dx * dx + dy * dy + 400; // epsilon to avoid divide by zero
        const dist = Math.sqrt(distSq);

        if (dist < 280) {
          // Inverse Square Gravitational Acceleration: F = G * m / r^2
          const force = (G * p.mass) / distSq;
          p.vx += (dx / dist) * force;
          p.vy += (dy / dist) * force;
        }
      }

      // Euler Integration Step
      p.vx *= damping;
      p.vy *= damping;
      p.x += p.vx;
      p.y += p.vy;

      // Boundary Collisions with Velocity Reflection
      if (p.x < 0) { p.x = 0; p.vx *= -1; }
      if (p.x > w) { p.x = w; p.vx *= -1; }
      if (p.y < 0) { p.y = 0; p.vy *= -1; }
      if (p.y > h) { p.y = h; p.vy *= -1; }
    }
  }

  // 3. Render Particles & Inter-Particle Constellation Network Lines
  drawParticles() {
    const ctx = this.ctx;
    const maxLinkDist = 140;

    // Draw connecting spring force lines between nearby nodes
    for (let i = 0; i < this.particles.length; i++) {
      for (let j = i + 1; j < this.particles.length; j++) {
        const p1 = this.particles[i];
        const p2 = this.particles[j];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < maxLinkDist) {
          const alpha = (1.0 - dist / maxLinkDist) * 0.22;
          ctx.strokeStyle = `rgba(${this.themeColor.r}, ${this.themeColor.g}, ${this.themeColor.b}, ${alpha})`;
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();
        }
      }
    }

    // Draw particle glowing nodes
    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${this.themeColor.r}, ${this.themeColor.g}, ${this.themeColor.b}, 0.65)`;
      ctx.shadowBlur = 10;
      ctx.shadowColor = `rgba(${this.themeColor.r}, ${this.themeColor.g}, ${this.themeColor.b}, 0.5)`;
      ctx.fill();
    }
    ctx.shadowBlur = 0;
  }

  animate() {
    this.time += 1;
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    this.drawHarmonicWaves();
    this.updatePhysics();
    this.drawParticles();

    requestAnimationFrame(() => this.animate());
  }
}

// Global Singleton Instance
let physicsBg = null;
document.addEventListener("DOMContentLoaded", () => {
  physicsBg = new MathPhysicsBackground("bg-canvas");
});
