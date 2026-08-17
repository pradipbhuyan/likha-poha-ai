/**
 * ChapterInfographicCard — mobile renderer for the ```chapter-infographic fence.
 *
 * Mirrors the web ChapterInfographicBlock.jsx: a full-chapter revision poster
 * shown at the end of a chapter's final lesson step.
 *
 * A poster is dense by nature, so at phone width the inline image is only a
 * preview — tapping opens a full-screen viewer where the image renders at a
 * readable scale and the student pans around it.
 *
 * Schema validation is NOT duplicated here — it comes from
 * shared/utils/chapterInfographic.js, the single source of truth both platforms
 * use, so a payload that renders on the web renders here too.
 */
import { useState } from "react";
import {
  Dimensions,
  Image,
  Modal,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

// Shape returned by validateChapterInfographic() in
// shared/utils/chapterInfographic.js. Declared here rather than imported
// because that module is plain JS with no exported types — the same convention
// ChapterJourney.tsx uses for the block types it mirrors from the backend.
export interface ChapterInfographic {
  url: string;
  alt: string;
  caption: string;
  width: number | null;
  height: number | null;
}

export default function ChapterInfographicCard({
  infographic,
}: {
  infographic: ChapterInfographic;
}) {
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);

  // A dead URL would otherwise leave an empty framed box with a caption under
  // it, which reads as a bug to the student.
  if (!infographic || failed) return null;

  const { url, alt, caption, width, height } = infographic;
  // Reserve the right box before the image arrives so the poster does not shove
  // the rest of the lesson down the page as it loads.
  const aspectRatio = width && height ? width / height : 1;

  const screen = Dimensions.get("window");
  // Render at ~2.2x screen width inside the viewer so panel text is legible and
  // the student pans, rather than fitting the whole poster to an unreadable
  // screen-width thumbnail.
  const viewerWidth = screen.width * 2.2;

  return (
    <View style={ciStyles.card}>
      <Text style={ciStyles.eyebrow}>CHAPTER AT A GLANCE</Text>

      <TouchableOpacity
        activeOpacity={0.85}
        onPress={() => setOpen(true)}
        accessibilityRole="imagebutton"
        accessibilityLabel={`${alt} — tap to enlarge`}
        style={ciStyles.frame}
      >
        <Image
          source={{ uri: url }}
          style={[ciStyles.image, { aspectRatio }]}
          resizeMode="contain"
          onError={() => setFailed(true)}
          accessible
          accessibilityLabel={alt}
        />
        <View style={ciStyles.zoomHint}>
          <Text style={ciStyles.zoomHintText}>🔍 Tap to enlarge</Text>
        </View>
      </TouchableOpacity>

      {caption ? <Text style={ciStyles.caption}>{caption}</Text> : null}

      <Modal
        visible={open}
        animationType="fade"
        onRequestClose={() => setOpen(false)}
        supportedOrientations={["portrait", "landscape"]}
      >
        <View style={ciStyles.viewer}>
          <View style={ciStyles.viewerBar}>
            <Text style={ciStyles.viewerTitle} numberOfLines={1}>
              {caption || "Chapter at a glance"}
            </Text>
            <TouchableOpacity
              onPress={() => setOpen(false)}
              accessibilityRole="button"
              accessibilityLabel="Close"
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            >
              <Text style={ciStyles.viewerClose}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Nested scrolls give two-axis panning: vertical outer, horizontal
              inner. RN has no pinch-zoom on Android, so an oversized image
              inside pannable scrolls is what makes the poster readable. */}
          <ScrollView
            style={ciStyles.viewerScroll}
            contentContainerStyle={ciStyles.viewerContent}
            maximumZoomScale={4}
            minimumZoomScale={1}
          >
            <ScrollView horizontal contentContainerStyle={ciStyles.viewerContent}>
              <Image
                source={{ uri: url }}
                style={{ width: viewerWidth, aspectRatio }}
                resizeMode="contain"
                accessible
                accessibilityLabel={alt}
              />
            </ScrollView>
          </ScrollView>
        </View>
      </Modal>
    </View>
  );
}

const ciStyles = StyleSheet.create({
  card: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#c7d2fe",
    borderRadius: 14,
    padding: 10,
    marginTop: 10,
    marginBottom: 12,
  },
  eyebrow: {
    fontSize: 10,
    fontWeight: "800",
    color: "#4f46e5",
    letterSpacing: 0.9,
    marginBottom: 8,
    paddingHorizontal: 2,
  },
  frame: {
    borderWidth: 1,
    borderColor: "#dbe2f5",
    borderRadius: 10,
    overflow: "hidden",
    backgroundColor: "#fff",
  },
  image: { width: "100%" },
  zoomHint: {
    position: "absolute",
    left: 8,
    right: 8,
    bottom: 8,
    backgroundColor: "rgba(15,23,42,.78)",
    borderRadius: 999,
    paddingVertical: 6,
    alignItems: "center",
  },
  zoomHintText: { color: "#fff", fontSize: 12, fontWeight: "700" },
  caption: { fontSize: 12.5, color: "#4c516d", lineHeight: 18, marginTop: 8, paddingHorizontal: 2 },
  viewer: { flex: 1, backgroundColor: "#020617" },
  viewerBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 52,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "rgba(148,163,184,.25)",
  },
  viewerTitle: { color: "#e2e8f0", fontSize: 13, fontWeight: "700", flexShrink: 1 },
  viewerClose: { color: "#cbd5e1", fontSize: 20, fontWeight: "600" },
  viewerScroll: { flex: 1 },
  viewerContent: { alignItems: "center", justifyContent: "center", padding: 12 },
});
