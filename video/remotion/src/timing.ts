export type SceneTiming = {
  id: number;
  startFrame: number;
  durationInFrames: number;
  durationSeconds: number;
};

export const SCENE_TIMINGS: SceneTiming[] = [
  {id: 1, startFrame: 0, durationInFrames: 1006, durationSeconds: 33.512},
  {id: 2, startFrame: 1006, durationInFrames: 1134, durationSeconds: 37.784},
  {id: 3, startFrame: 2140, durationInFrames: 1520, durationSeconds: 50.648},
  {id: 4, startFrame: 3660, durationInFrames: 1282, durationSeconds: 42.704},
  {id: 5, startFrame: 4942, durationInFrames: 2759, durationSeconds: 91.952},
  {id: 6, startFrame: 7701, durationInFrames: 1148, durationSeconds: 38.264},
  {id: 7, startFrame: 8849, durationInFrames: 1228, durationSeconds: 40.904},
  {id: 8, startFrame: 10077, durationInFrames: 911, durationSeconds: 30.344},
];
export const TOTAL_FRAMES = 10988;
