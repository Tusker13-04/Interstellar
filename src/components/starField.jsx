import { useEffect, useRef } from "react";
import * as THREE from "three";

const Starfield = () => {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;

    const mountNode = mountRef.current;
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      1,
      2000
    );
    camera.position.z = 5;

    const renderer = new THREE.WebGLRenderer();
    renderer.setSize(window.innerWidth, window.innerHeight);
    mountNode.appendChild(renderer.domElement);

    const light = new THREE.AmbientLight(0xffffff, 2);
    scene.add(light);

    const stars = [];
    for (let z = -2000; z < 2000; z += 5) {
      const geometry = new THREE.SphereGeometry(0.6, 16, 16);
      const material = new THREE.MeshStandardMaterial({
        color: 0xffffff,
        emissive: 0xffffff,
        emissiveIntensity: 2,
      });
      const sphere = new THREE.Mesh(geometry, material);

      sphere.position.x = Math.random() * 1000 - 500;
      sphere.position.y = Math.random() * 1000 - 500;
      sphere.position.z = z;
      sphere.scale.set(1.5, 1.5, 1.5);

      scene.add(sphere);
      stars.push(sphere);
    }

    const animate = () => {
      requestAnimationFrame(animate);
      stars.forEach((star, i) => {
        star.position.z += i / 300;
        if (star.position.z > 1000) star.position.z -= 3000;
      });
      renderer.render(scene, camera);
    };

    animate();

    return () => {
      if (mountNode) mountNode.removeChild(renderer.domElement);
    };
  }, []);

  return <div ref={mountRef} className="absolute inset-0 -z-10"></div>;
};

export default Starfield;
