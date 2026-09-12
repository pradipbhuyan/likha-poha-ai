import { Capacitor } from "@capacitor/core";
import { Filesystem, Directory } from "@capacitor/filesystem";
import { Share } from "@capacitor/share";

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

/**
 * Saves a Blob so the user can get it off the device.
 * Web: triggers the normal browser download.
 * Native (Capacitor): the `<a download>` trick doesn't save files in a WebView,
 * so instead this writes to app cache storage and opens the native share sheet.
 */
export async function saveOrShareBlob(blob, filename) {
  if (!Capacitor.isNativePlatform()) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
    return;
  }

  const base64Data = await blobToBase64(blob);
  const { uri } = await Filesystem.writeFile({
    path: filename,
    data: base64Data,
    directory: Directory.Cache,
  });
  await Share.share({ url: uri, title: filename });
}

/**
 * Same idea as saveOrShareBlob, but for a jsPDF document. On web this calls
 * doc.save() completely unchanged (existing behavior/tests rely on it being
 * called directly) — only native gets routed through Filesystem/Share.
 */
export async function saveOrSharePdf(doc, filename) {
  if (!Capacitor.isNativePlatform()) {
    doc.save(filename);
    return;
  }
  await saveOrShareBlob(doc.output("blob"), filename);
}
