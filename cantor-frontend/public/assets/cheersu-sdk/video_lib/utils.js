// 综合推荐方案
export const browserDeviceType = () => {
  const ua = navigator.userAgent;
  const isIPad =
    /iPad/i.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

  if (isIPad) {
    console.log("browser device type is ipad, return phone");
    return "phone";
  }

  const isMobile =
    /Android|webOS|iPhone|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua);
  const width = window.innerWidth;

  if (isMobile && width <= 768) {
    console.log("browser device type is phone, return phone");
    return "phone";
  }

  if (width <= 1024 && "ontouchstart" in window) {
    console.log("browser device type is tablet, return phone");
    return "phone";
  }
  console.log("browser device type is pc, return pc");
  return "pc";
};
