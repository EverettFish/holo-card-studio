export function hand(x, pose = 'open') {
  const p = Array.from({ length: 21 }, () => ({ x, y: 0.5, z: 0 }));
  p[0] = { x, y: 0.65, z: 0 };
  for (const [i, dx] of [[5,-.05],[9,0],[13,.03],[17,.06]]) p[i] = { x:x+dx,y:.5,z:0 };
  p[4] = { x:x+.01,y:.42,z:0 };
  p[8] = { x:x-.12,y:.28,z:0 };
  p[12] = { x:x+(pose==='contact'?.013:.16),y:.42,z:0 };
  if (pose==='index-pinch') p[8] = {...p[4]};
  return p;
}
export const pair = (distance, swapped = false) => {
  const hands = [hand(.5-distance/2),hand(.5+distance/2)];
  return swapped ? hands.reverse() : hands;
};
