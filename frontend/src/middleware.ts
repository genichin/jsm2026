import { NextResponse, NextRequest } from "next/server";

export function middleware(req: NextRequest) {
  // HTTPS 강제 리다이렉트 비활성화 (HTTP 개발 모드 허용)
  // Production에서는 리버스 프록시(Nginx/Caddy)가 HTTPS 처리
  
  // const proto = req.headers.get("x-forwarded-proto") || req.nextUrl.protocol.replace(":", "");
  // const isSecure = proto === "https";
  // if (!isSecure) {
  //   const url = req.nextUrl;
  //   url.protocol = "https";
  //   return NextResponse.redirect(url, 308);
  // }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
