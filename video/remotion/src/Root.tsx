import {Composition} from "remotion";
import {DebugMateVideo, DebugMateVisual} from "./DebugMateVideo";
import {TOTAL_FRAMES} from "./timing";

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="DebugMateV01"
        component={DebugMateVideo}
        defaultProps={{includeAudio: true}}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="DebugMateV01Visual"
        component={DebugMateVisual}
        durationInFrames={TOTAL_FRAMES}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
