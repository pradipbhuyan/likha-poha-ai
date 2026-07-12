/**
 * BARE MINIMUM test — no expo-router, no native modules.
 * Uses registerRootComponent to bypass expo-router entirely.
 */
import { registerRootComponent } from "expo";
import MinimalApp from "./MinimalApp";

registerRootComponent(MinimalApp);
