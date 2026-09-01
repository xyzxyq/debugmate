import {Config} from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setCodec("h264");
Config.setCrf(18);
Config.setPixelFormat("yuv420p");
Config.setAudioCodec("aac");
Config.setAudioBitrate("192k");
