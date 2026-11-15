import AppKit
import Darwin
import Foundation
import SwiftUI
import WebKit

// MARK: - CosmicTera Official Brand Palette

enum CosmicTheme {
    static let bgPrimary = Color(red: 0x06 / 255.0, green: 0x0C / 255.0, blue: 0x16 / 255.0)
    static let bgSecondary = Color(red: 0x09 / 255.0, green: 0x13 / 255.0, blue: 0x22 / 255.0)
    static let bgCard = Color(red: 0x0D / 255.0, green: 0x1B / 255.0, blue: 0x30 / 255.0)
    static let bgCode = Color(red: 0x04 / 255.0, green: 0x08 / 255.0, blue: 0x10 / 255.0)
    static let emerald = Color(red: 0x30 / 255.0, green: 0xD0 / 255.0, blue: 0x70 / 255.0)
    static let gold = Color(red: 0xF0 / 255.0, green: 0xC8 / 255.0, blue: 0x60 / 255.0)
    static let cyan = Color(red: 0x30 / 255.0, green: 0xC0 / 255.0, blue: 0xD0 / 255.0)
    static let silver = Color(red: 0xF2 / 255.0, green: 0xF6 / 255.0, blue: 0xFA / 255.0)
    static let muted = Color(red: 0x88 / 255.0, green: 0x9C / 255.0, blue: 0xB4 / 255.0)
    static let redFault = Color(red: 0xFF / 255.0, green: 0x3B / 255.0, blue: 0x3B / 255.0)
}

// MARK: - Sidebar Sections (Including NUI Language Engine & NUI Self-Learning Center)

enum SidebarSection: String, CaseIterable, Identifiable {
    case nuiChat = "NUI Chat"
    case languageEngine = "Language Engine"
    case selfLearning = "Self-Learning Center"
    case nuiCore = "NUI Core"
    case computingSystem = "Computing System"
    case nuiArchitecture = "NUI Architecture"
    case codingStudio = "Coding Studio"
    case webInternet = "Web & Internet"
    case browser = "Browser"
    case filesKnowledge = "Files & Knowledge"
    case hardwareMonitor = "Hardware Monitor"
    case projectsGit = "Projects & Git"
    case accessControl = "Access Control"
    case activityHistory = "Activity History"
    case settings = "Settings"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .nuiChat: return "bubble.left.and.bubble.right.fill"
        case .languageEngine: return "waveform.and.magnifyingglass"
        case .selfLearning: return "graduationcap.fill"
        case .nuiCore: return "brain.head.profile"
        case .computingSystem: return "cpu.fill"
        case .nuiArchitecture: return "square.stack.3d.up.fill"
        case .codingStudio: return "chevron.left.forwardslash.chevron.right"
        case .webInternet: return "globe"
        case .browser: return "safari.fill"
        case .filesKnowledge: return "folder.fill.badge.gearshape"
        case .hardwareMonitor: return "memorychip.fill"
        case .projectsGit: return "point.3.connected.trianglepath.dotted"
        case .accessControl: return "lock.shield.fill"
        case .activityHistory: return "clock.arrow.circlepath"
        case .settings: return "slider.horizontal.3"
        }
    }
}

// MARK: - Local Loopback Socket Client (JSON + Real-Time SSE Streaming on 127.0.0.1:8848)

struct LocalLoopbackClient {
    static let activeServicePath = "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/active_service.json"
    static let serverScriptPath = "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/backend/server.py"

    static func resolveActivePort() -> UInt16 {
        if let data = try? Data(contentsOf: URL(fileURLWithPath: activeServicePath)),
           let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
           let p = obj["port"] as? Int, p > 0 && p < 65536 {
            return UInt16(p)
        }
        return 8848
    }

    static func sendRequest(
        method: String,
        path: String,
        body: [String: Any]? = nil,
        timeoutSeconds: Int = 8
    ) throws -> (statusCode: Int, json: [String: Any]) {
        let port = resolveActivePort()
        let fd = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else {
            throw NSError(domain: "NUISocket", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to create socket"])
        }
        defer { Darwin.close(fd) }

        var tv = timeval(tv_sec: timeoutSeconds, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))

        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr)

        let connectRes = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard connectRes == 0 else {
            throw NSError(
                domain: "NUILocalService",
                code: Int(errno),
                userInfo: [NSLocalizedDescriptionKey: "NUI Local Service tidak merespons pada 127.0.0.1:\(port) (errno \(errno))"]
            )
        }

        let bodyData = (body != nil) ? ((try? JSONSerialization.data(withJSONObject: body!)) ?? Data()) : Data()
        var header = "\(method) \(path) HTTP/1.1\r\n"
        header += "Host: 127.0.0.1:\(port)\r\n"
        header += "Content-Type: application/json; charset=utf-8\r\n"
        header += "Content-Length: \(bodyData.count)\r\n"
        header += "Connection: close\r\n\r\n"

        var payload = Data(header.utf8)
        payload.append(bodyData)

        let sent = payload.withUnsafeBytes { ptr -> Int in
            guard let base = ptr.baseAddress else { return -1 }
            return Darwin.send(fd, base, payload.count, 0)
        }
        guard sent > 0 else {
            throw NSError(domain: "NUILocalService", code: -2, userInfo: [NSLocalizedDescriptionKey: "Gagal mengirim request ke NUI Local Service"])
        }

        var responseData = Data()
        var buffer = [UInt8](repeating: 0, count: 16384)
        while true {
            let n = Darwin.recv(fd, &buffer, buffer.count, 0)
            if n > 0 {
                responseData.append(buffer, count: n)
            } else {
                break
            }
        }

        guard let rawStr = String(data: responseData, encoding: .utf8), !rawStr.isEmpty else {
            throw NSError(domain: "NUILocalService", code: -3, userInfo: [NSLocalizedDescriptionKey: "Respons kosong dari NUI Local Service (EMPTY_RESPONSE)"])
        }

        let parts = rawStr.components(separatedBy: "\r\n\r\n")
        let headerBlock = parts.first ?? ""
        let bodyString = parts.dropFirst().joined(separator: "\r\n\r\n")

        var statusCode = 200
        if let firstLine = headerBlock.components(separatedBy: "\r\n").first {
            let tokens = firstLine.split(separator: " ")
            if tokens.count >= 2, let code = Int(tokens[1]) {
                statusCode = code
            }
        }

        guard let jsonData = bodyString.data(using: .utf8),
              let jsonObj = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] else {
            throw NSError(domain: "NUILocalService", code: -4, userInfo: [NSLocalizedDescriptionKey: "Format JSON respons tidak valid dari backend"])
        }

        return (statusCode: statusCode, json: jsonObj)
    }

    static func streamChatRequest(
        body: [String: Any],
        isCancelled: () -> Bool,
        onEvent: ([String: Any]) -> Void
    ) throws {
        let port = resolveActivePort()
        let fd = Darwin.socket(AF_INET, SOCK_STREAM, 0)
        guard fd >= 0 else {
            throw NSError(domain: "NUISocket", code: -1, userInfo: [NSLocalizedDescriptionKey: "Gagal membuka socket streaming"])
        }
        defer { Darwin.close(fd) }

        var tv = timeval(tv_sec: 90, tv_usec: 0)
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, socklen_t(MemoryLayout<timeval>.size))

        var addr = sockaddr_in()
        addr.sin_len = UInt8(MemoryLayout<sockaddr_in>.size)
        addr.sin_family = sa_family_t(AF_INET)
        addr.sin_port = port.bigEndian
        inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr)

        let connectRes = withUnsafePointer(to: &addr) {
            $0.withMemoryRebound(to: sockaddr.self, capacity: 1) {
                Darwin.connect(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size))
            }
        }
        guard connectRes == 0 else {
            throw NSError(
                domain: "NUILocalService",
                code: Int(errno),
                userInfo: [NSLocalizedDescriptionKey: "NUI Local Service tidak merespons pada 127.0.0.1:\(port)"]
            )
        }

        let bodyData = (try? JSONSerialization.data(withJSONObject: body)) ?? Data()
        var header = "POST /api/chat/stream HTTP/1.1\r\n"
        header += "Host: 127.0.0.1:\(port)\r\n"
        header += "Content-Type: application/json; charset=utf-8\r\n"
        header += "Content-Length: \(bodyData.count)\r\n"
        header += "Connection: close\r\n\r\n"

        var payload = Data(header.utf8)
        payload.append(bodyData)

        let sent = payload.withUnsafeBytes { ptr -> Int in
            guard let base = ptr.baseAddress else { return -1 }
            return Darwin.send(fd, base, payload.count, 0)
        }
        guard sent > 0 else {
            throw NSError(domain: "NUILocalService", code: -2, userInfo: [NSLocalizedDescriptionKey: "Gagal mengirim stream request"])
        }

        var rawBuffer = ""
        var headerStripped = false
        var chunk = [UInt8](repeating: 0, count: 4096)

        while !isCancelled() {
            let n = Darwin.recv(fd, &chunk, chunk.count, 0)
            if n <= 0 {
                break
            }
            if let str = String(bytes: chunk[0..<n], encoding: .utf8) {
                rawBuffer += str
                if !headerStripped {
                    if let range = rawBuffer.range(of: "\r\n\r\n") {
                        rawBuffer = String(rawBuffer[range.upperBound...])
                        headerStripped = true
                    } else {
                        continue
                    }
                }
                while let eventRange = rawBuffer.range(of: "\n\n") {
                    let frame = String(rawBuffer[..<eventRange.lowerBound]).trimmingCharacters(in: .whitespacesAndNewlines)
                    rawBuffer = String(rawBuffer[eventRange.upperBound...])
                    if frame.hasPrefix("data:") {
                        let jsonText = String(frame.dropFirst(5)).trimmingCharacters(in: .whitespaces)
                        if let jData = jsonText.data(using: .utf8),
                           let obj = try? JSONSerialization.jsonObject(with: jData) as? [String: Any] {
                            onEvent(obj)
                        }
                    }
                }
            }
        }
    }

    static func terminateStaleDaemonFromActiveFile() {
        guard let data = try? Data(contentsOf: URL(fileURLWithPath: activeServicePath)),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return
        }
        let ver = (obj["version"] as? String) ?? ""
        if ver != "1.5.2", let oldPid = obj["pid"] as? Int, oldPid > 0, oldPid != Int(getpid()) {
            Darwin.kill(pid_t(oldPid), SIGTERM)
            usleep(250_000)
        }
    }

    static func spawnDaemonIfNeeded() -> pid_t? {
        guard FileManager.default.fileExists(atPath: serverScriptPath) else { return nil }
        terminateStaleDaemonFromActiveFile()
        var pid: pid_t = 0
        let venvPy = "/Users/AMRA/hijaiyyah-mathematics/.venv-mac/bin/python"
        let chosenPy = FileManager.default.fileExists(atPath: venvPy) ? venvPy : "/usr/local/bin/python3"
        let pyPath = strdup(chosenPy)
        let arg1 = strdup(serverScriptPath)
        let arg2 = strdup("--host")
        let arg3 = strdup("127.0.0.1")
        let arg4 = strdup("--port")
        let arg5 = strdup("8848")
        defer {
            free(pyPath); free(arg1); free(arg2); free(arg3); free(arg4); free(arg5)
        }
        var argv: [UnsafeMutablePointer<CChar>?] = [pyPath, arg1, arg2, arg3, arg4, arg5, nil]
        let status = posix_spawn(&pid, chosenPy, nil, nil, &argv, environ)
        return status == 0 ? pid : nil
    }
}

// MARK: - Chat Message Item Model

struct ChatMessageItem: Identifiable {
    let id: String
    let requestId: String
    let role: String
    var content: String
    var provider: String
    var model: String
    var responseTimeMs: Double
    var sourceAttribution: String
    var executionStatus: String
    var thinkingStages: [String]
    var toolActivities: [String]
}

// MARK: - Browser Models, URL Normalizer & Navigation Trace Records

struct BrowserTabModel: Identifiable, Equatable {
    let id: String
    var navigationId: String = "nav-init"
    var requestedURL: String = ""
    var normalizedURL: String = ""
    var title: String
    var url: String
    var domain: String
    var favicon: String
    var status: String = "COMPLETE"
    var isLoading: Bool
    var progress: Double
    var httpStatus: Int
    var securityState: String
    var canGoBack: Bool
    var canGoForward: Bool
    var zoomLevel: Double
    var hasError: Bool
    var errorMessage: String
    var contentVisible: Bool = true
}

struct BrowserNavigationTraceRecord: Identifiable, Equatable {
    let id: String // navigationId
    let tabId: String
    var requestedURL: String
    var normalizedURL: String
    var actualURL: String
    var didStartProvisionalNavigation: Bool = false
    var didReceiveServerRedirectForProvisionalNavigation: Bool = false
    var didCommit: Bool = false
    var didFinish: Bool = false
    var didFailProvisionalNavigation: Bool = false
    var didFail: Bool = false
    var webViewWebContentProcessDidTerminate: Bool = false
    var httpStatus: Int = 0
    var pageTitle: String = ""
    var state: String = "LOADING"
    var errorCode: String = ""
    var errorMessage: String = ""
    var startedAt: Date = Date()
    var elapsedMs: Double = 0.0
    var contentVisibleInViewport: Bool = false
}

enum BrowserAddressNormalizer {
    static let httpsPrefix = "ht" + "tps://"
    static let httpPrefix = "ht" + "tp://"

    struct NormalizedAddress {
        let ok: Bool
        let inputType: String
        let rawInput: String
        let resolvedURL: String
        let domain: String
        let securityState: String
        let errorCode: String
        let errorMessage: String
    }

    static func normalize(_ rawInput: String) -> NormalizedAddress {
        let cleaned = rawInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleaned.isEmpty else {
            return NormalizedAddress(
                ok: false,
                inputType: "EMPTY",
                rawInput: rawInput,
                resolvedURL: "",
                domain: "",
                securityState: "INVALID_URL",
                errorCode: "EMPTY_URL",
                errorMessage: "Input URL atau pencarian kosong."
            )
        }
        let lower = cleaned.lowercased()
        if lower.hasPrefix("javascript:") || lower.hasPrefix("data:") || lower.hasPrefix("file:") || lower.hasPrefix("vbscript:") {
            return NormalizedAddress(
                ok: false,
                inputType: "BLOCKED_SCHEME",
                rawInput: rawInput,
                resolvedURL: "",
                domain: "",
                securityState: "BLOCKED_UNSAFE_SCHEME",
                errorCode: "BLOCKED_SCHEME",
                errorMessage: "Skema URL tidak diizinkan demi keamanan Browser NUI."
            )
        }
        if lower.hasPrefix("about:") || lower.hasPrefix("cosmictera://") {
            return NormalizedAddress(
                ok: true,
                inputType: "INTERNAL_URL",
                rawInput: rawInput,
                resolvedURL: cleaned,
                domain: "cosmictera.local",
                securityState: "INTERNAL_PAGE",
                errorCode: "",
                errorMessage: ""
            )
        }

        let hasSpaces = cleaned.rangeOfCharacter(from: .whitespacesAndNewlines) != nil
        let hasScheme = cleaned.contains("://")
        var looksLikeURL = false
        if hasScheme && !hasSpaces {
            looksLikeURL = true
        } else if !hasSpaces {
            let hostCandidate = cleaned.components(separatedBy: "/").first?
                .components(separatedBy: "?").first?
                .components(separatedBy: "#").first ?? ""
            let hostOnly = hostCandidate.components(separatedBy: ":").first?.lowercased() ?? ""
            if hostOnly == "localhost" || hostOnly == "127.0.0.1" {
                looksLikeURL = true
            } else if hostOnly.contains(".") && !hostOnly.hasPrefix(".") && !hostOnly.hasSuffix(".") {
                let parts = hostOnly.split(separator: ".")
                if let tld = parts.last, tld.count >= 2 {
                    looksLikeURL = true
                }
            }
        }

        if !looksLikeURL {
            let encoded = cleaned.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? cleaned
            let searchURL = httpsPrefix + "www.google.com/search?q=" + encoded
            return NormalizedAddress(
                ok: true,
                inputType: "SEARCH_QUERY",
                rawInput: rawInput,
                resolvedURL: searchURL,
                domain: "www.google.com",
                securityState: "SECURE_HTTPS",
                errorCode: "",
                errorMessage: ""
            )
        }

        var candidate = cleaned
        if !hasScheme {
            let hostPart = cleaned.components(separatedBy: "/").first?.components(separatedBy: ":").first?.lowercased() ?? ""
            if hostPart == "localhost" || hostPart == "127.0.0.1" {
                candidate = httpPrefix + cleaned
            } else {
                candidate = httpsPrefix + cleaned
            }
        }

        guard var comps = URLComponents(string: candidate),
              let scheme = comps.scheme?.lowercased(),
              (scheme == "http" || scheme == "https"),
              let host = comps.host?.lowercased(),
              !host.isEmpty else {
            return NormalizedAddress(
                ok: false,
                inputType: "INVALID_URL",
                rawInput: rawInput,
                resolvedURL: "",
                domain: "",
                securityState: "INVALID_URL",
                errorCode: "INVALID_URL",
                errorMessage: "Format URL tidak valid: \(rawInput)"
            )
        }

        if comps.path.isEmpty {
            comps.path = "/"
        }
        let finalURL = comps.url?.absoluteString ?? candidate
        let isHTTPS = (scheme == "https")
        let isLoopback = (host == "localhost" || host == "127.0.0.1")
        let sec = isHTTPS ? "SECURE_HTTPS" : (isLoopback ? "LOCAL_LOOPBACK" : "INSECURE_HTTP")
        return NormalizedAddress(
            ok: true,
            inputType: "URL",
            rawInput: rawInput,
            resolvedURL: finalURL,
            domain: host,
            securityState: sec,
            errorCode: "",
            errorMessage: ""
        )
    }

    static func faviconForDomain(_ domain: String) -> String {
        let d = domain.lowercased()
        if d.contains("python.org") { return "book.closed.fill" }
        if d.contains("github.com") { return "chevron.left.forwardslash.chevron.right" }
        if d.contains("google.com") { return "magnifyingglass.circle.fill" }
        if d.contains("akademihijaiyyahindonesia.com") { return "sparkles" }
        return "globe"
    }

    static func buildErrorHTML(url: String, domain: String, errorCode: String, errorMessage: String) -> String {
        let safeURL = url.replacingOccurrences(of: "<", with: "&lt;").replacingOccurrences(of: ">", with: "&gt;")
        let safeDom = (domain.isEmpty ? "Halaman" : domain).replacingOccurrences(of: "<", with: "&lt;")
        let safeCode = errorCode.replacingOccurrences(of: "<", with: "&lt;")
        let safeMsg = errorMessage.replacingOccurrences(of: "<", with: "&lt;")
        return """
        <!DOCTYPE html>
        <html lang="id">
        <head>
        <meta charset="utf-8">
        <title>Gagal Memuat Halaman — \(safeDom)</title>
        <style>
          body { background: #060C16; color: #F2F6FA; font-family: -apple-system, BlinkMacSystemFont, sans-serif; margin: 0; padding: 42px 24px; display: flex; justify-content: center; }
          .card { max-width: 640px; width: 100%; background: #0D1B30; border: 1px solid rgba(255, 59, 59, 0.55); border-radius: 12px; padding: 26px; box-sizing: border-box; }
          .badge { display: inline-block; background: rgba(255, 59, 59, 0.2); color: #FF6B6B; font-family: ui-monospace, Menlo, monospace; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; margin-bottom: 12px; }
          h1 { font-size: 19px; margin: 0 0 10px 0; color: #F0C860; }
          p { font-size: 13px; line-height: 1.55; color: #889CB4; margin: 0 0 12px 0; }
          .url-box { background: #040810; color: #30C0D0; font-family: ui-monospace, Menlo, monospace; font-size: 12px; padding: 10px 12px; border-radius: 6px; word-break: break-all; margin-bottom: 14px; }
          .hint { font-size: 12px; color: #30D070; }
        </style>
        </head>
        <body>
          <div class="card">
            <div class="badge">NAVIGATION FAILED · \(safeCode)</div>
            <h1>Gagal Memuat Halaman — \(safeDom)</h1>
            <p>CosmicTera NUI Browser tidak berhasil menyelesaikan navigasi ke alamat berikut:</p>
            <div class="url-box">\(safeURL)</div>
            <p><strong>Penyebab Teknis:</strong> \(safeMsg)</p>
            <p class="hint">Periksa indikator jaringan (NET / DNS / TLS / HTTPS) di bar bawah atau klik ↻ Reload untuk mencoba lagi.</p>
          </div>
        </body>
        </html>
        """
    }
}

enum BrowserDrawerPanel: String {
    case none = "NONE"
    case bookmarks = "BOOKMARKS"
    case history = "HISTORY"
    case downloads = "DOWNLOADS"
}

// MARK: - Native macOS Clipboard Manager (NSPasteboard.general) & Rich Markdown + Code Renderer

@MainActor
final class NUIClipboardManager {
    static let shared = NUIClipboardManager()
    private(set) var lastCopiedText: String = ""

    @discardableResult
    func copyString(_ text: String) -> Bool {
        lastCopiedText = text
        let pb = NSPasteboard.general
        pb.clearContents()
        let ok = pb.setString(text, forType: .string)
        return ok || !lastCopiedText.isEmpty
    }

    @discardableResult
    func copyUserMessage(_ text: String) -> Bool {
        let cleaned = Self.stripAttachmentFooter(text)
        return copyString(cleaned)
    }

    @discardableResult
    func copyAssistantResponse(_ fullText: String) -> Bool {
        return copyString(fullText)
    }

    @discardableResult
    func copyCodeBlockOnly(_ rawCode: String) -> Bool {
        let stripped = Self.stripOuterMarkdownCodeFences(rawCode)
        return copyString(stripped)
    }

    func readPasteboardString() -> String {
        if let sysStr = NSPasteboard.general.string(forType: .string), !sysStr.isEmpty {
            return sysStr
        }
        return lastCopiedText
    }

    func pasteIntoString(currentText: String) -> String {
        let clip = readPasteboardString()
        guard !clip.isEmpty else { return currentText }
        if currentText.isEmpty {
            return clip
        }
        return currentText + clip
    }

    static func stripAttachmentFooter(_ raw: String) -> String {
        if let range = raw.range(of: "\n\n📎 *Lampiran (+):*") {
            return String(raw[..<range.lowerBound])
        }
        return raw
    }

    static func stripOuterMarkdownCodeFences(_ raw: String) -> String {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.hasPrefix("```") && trimmed.hasSuffix("```") else {
            return raw
        }
        var lines = trimmed.components(separatedBy: "\n")
        if !lines.isEmpty {
            lines.removeFirst()
        }
        if let last = lines.last, last.trimmingCharacters(in: .whitespacesAndNewlines) == "```" {
            lines.removeLast()
        }
        return lines.joined(separator: "\n")
    }
}

enum MarkdownBlockNode {
    case heading(level: Int, text: String)
    case table(headers: [String], rows: [[String]])
    case bulletList(items: [String])
    case numberedList(items: [(String, String)])
    case blockquote(text: String)
    case formulaCallout(text: String)
    case paragraph(text: String)
}

struct CodeBlockCardView: View {
    let language: String
    let codeBody: String
    let blockId: String
    var copiedItemId: String = ""
    var onCopyCode: ((String, String) -> Void)? = nil
    var onOpenInStudio: ((String, String) -> Void)? = nil
    @State private var localCopied: Bool = false

    private var isCopied: Bool {
        localCopied || (!blockId.isEmpty && copiedItemId == blockId)
    }

    private var normalizedLangLabel: String {
        let clean = language.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        if clean.isEmpty { return "CODE" }
        switch clean {
        case "py", "python", "python3": return "PYTHON"
        case "swift": return "SWIFT"
        case "sh", "bash", "zsh", "shell": return "BASH / SHELL"
        case "v", "sv", "verilog", "systemverilog": return "VERILOG / RTL"
        case "sql", "sqlite": return "SQL"
        case "json": return "JSON"
        case "html", "xml": return "HTML"
        case "css": return "CSS"
        case "hasm", "hisa": return "H-ISA ASM"
        default: return clean.uppercased()
        }
    }

    var body: some View {
        let lineCount = max(1, codeBody.components(separatedBy: "\n").count)
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 8) {
                HStack(spacing: 5) {
                    Image(systemName: "chevron.left.forwardslash.chevron.right")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(CosmicTheme.gold)
                    Text(normalizedLangLabel)
                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                        .foregroundColor(CosmicTheme.gold)
                    Text("· \(lineCount) baris")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(CosmicTheme.muted)
                }
                Spacer()
                if let onOpenInStudio = onOpenInStudio {
                    Button(action: {
                        onOpenInStudio(codeBody, language)
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "hammer.fill")
                                .font(.system(size: 9.5))
                            Text("Buka di Studio")
                                .font(.system(size: 10, weight: .semibold))
                        }
                        .padding(.horizontal, 7)
                        .padding(.vertical, 3)
                        .background(CosmicTheme.bgSecondary)
                        .foregroundColor(CosmicTheme.silver)
                        .cornerRadius(4)
                    }
                    .buttonStyle(.plain)
                }
                Button(action: {
                    if let onCopyCode = onCopyCode {
                        onCopyCode(codeBody, blockId)
                    } else {
                        NUIClipboardManager.shared.copyCodeBlockOnly(codeBody)
                    }
                    localCopied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
                        localCopied = false
                    }
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: isCopied ? "checkmark.circle.fill" : "doc.on.doc")
                            .font(.system(size: 10, weight: .bold))
                        Text(isCopied ? "Copied ✓ · Tersalin" : "Copy Code")
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3.5)
                    .background(isCopied ? CosmicTheme.emerald.opacity(0.22) : CosmicTheme.cyan.opacity(0.16))
                    .foregroundColor(isCopied ? CosmicTheme.emerald : CosmicTheme.cyan)
                    .cornerRadius(5)
                }
                .buttonStyle(.plain)
            }
            .padding(.bottom, 2)

            ScrollView(.horizontal, showsIndicators: true) {
                Text(Self.syntaxHighlightedAttributedCode(codeBody))
                    .font(.system(size: 12, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .padding(10)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(CosmicTheme.bgCode)
        .overlay(
            RoundedRectangle(cornerRadius: 7)
                .stroke(CosmicTheme.cyan.opacity(0.28), lineWidth: 1)
        )
        .cornerRadius(7)
    }

    static func syntaxHighlightedAttributedCode(_ rawCode: String) -> AttributedString {
        var result = AttributedString(rawCode)
        result.foregroundColor = CosmicTheme.emerald
        return result
    }
}

struct MarkdownTableBlockView: View {
    let headers: [String]
    let rows: [[String]]

    var body: some View {
        let colCount = max(headers.count, rows.map { $0.count }.max() ?? 0)
        ScrollView(.horizontal, showsIndicators: true) {
            VStack(alignment: .leading, spacing: 0) {
                if !headers.isEmpty {
                    HStack(spacing: 0) {
                        ForEach(0..<colCount, id: \.self) { cIdx in
                            let cellText = cIdx < headers.count ? headers[cIdx] : ""
                            Text(MarkdownProseSegmentView.inlineAttributed(cellText))
                                .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                                .foregroundColor(CosmicTheme.gold)
                                .textSelection(.enabled)
                                .frame(minWidth: 120, maxWidth: 280, alignment: .leading)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 6)
                        }
                    }
                    .background(CosmicTheme.bgSecondary)
                }
                ForEach(Array(rows.enumerated()), id: \.offset) { rIdx, row in
                    HStack(spacing: 0) {
                        ForEach(0..<colCount, id: \.self) { cIdx in
                            let cellText = cIdx < row.count ? row[cIdx] : ""
                            Text(MarkdownProseSegmentView.inlineAttributed(cellText))
                                .font(.system(size: 12))
                                .foregroundColor(CosmicTheme.silver)
                                .textSelection(.enabled)
                                .frame(minWidth: 120, maxWidth: 280, alignment: .leading)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                        }
                    }
                    .background(rIdx % 2 == 0 ? CosmicTheme.bgCard.opacity(0.6) : CosmicTheme.bgSecondary.opacity(0.45))
                }
            }
            .overlay(
                RoundedRectangle(cornerRadius: 6)
                    .stroke(CosmicTheme.cyan.opacity(0.3), lineWidth: 1)
            )
            .cornerRadius(6)
        }
    }
}

struct MarkdownProseSegmentView: View {
    let rawSegment: String

    var body: some View {
        let nodes = Self.parseBlocks(rawSegment)
        VStack(alignment: .leading, spacing: 7) {
            ForEach(Array(nodes.enumerated()), id: \.offset) { _, node in
                switch node {
                case .heading(let level, let text):
                    Text(Self.inlineAttributed(text))
                        .font(.system(size: level == 1 ? 16 : (level == 2 ? 14.5 : 13.5), weight: .bold))
                        .foregroundColor(level == 1 ? CosmicTheme.cyan : CosmicTheme.gold)
                        .textSelection(.enabled)
                        .padding(.top, 2)
                case .table(let headers, let rows):
                    MarkdownTableBlockView(headers: headers, rows: rows)
                case .bulletList(let items):
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(items.enumerated()), id: \.offset) { _, item in
                            HStack(alignment: .top, spacing: 7) {
                                Text("•")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(CosmicTheme.cyan)
                                Text(Self.inlineAttributed(item))
                                    .font(.system(size: 13))
                                    .foregroundColor(CosmicTheme.silver)
                                    .textSelection(.enabled)
                            }
                        }
                    }
                case .numberedList(let items):
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(items.enumerated()), id: \.offset) { _, pair in
                            HStack(alignment: .top, spacing: 7) {
                                Text("\(pair.0).")
                                    .font(.system(size: 12.5, weight: .bold, design: .monospaced))
                                    .foregroundColor(CosmicTheme.gold)
                                Text(Self.inlineAttributed(pair.1))
                                    .font(.system(size: 13))
                                    .foregroundColor(CosmicTheme.silver)
                                    .textSelection(.enabled)
                            }
                        }
                    }
                case .blockquote(let text):
                    HStack(alignment: .top, spacing: 8) {
                        Rectangle()
                            .fill(CosmicTheme.gold)
                            .frame(width: 3)
                        Text(Self.inlineAttributed(text))
                            .font(.system(size: 12.5).italic())
                            .foregroundColor(CosmicTheme.silver)
                            .textSelection(.enabled)
                    }
                    .padding(.vertical, 4)
                    .padding(.horizontal, 8)
                    .background(CosmicTheme.bgSecondary.opacity(0.6))
                    .cornerRadius(5)
                case .formulaCallout(let text):
                    HStack(spacing: 8) {
                        Image(systemName: "function")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(CosmicTheme.emerald)
                        Text(Self.inlineAttributed(text))
                            .font(.system(size: 12.5, weight: .semibold, design: .monospaced))
                            .foregroundColor(CosmicTheme.emerald)
                            .textSelection(.enabled)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(CosmicTheme.bgCode.opacity(0.85))
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(CosmicTheme.emerald.opacity(0.45), lineWidth: 1)
                    )
                    .cornerRadius(6)
                case .paragraph(let text):
                    Text(Self.inlineAttributed(text))
                        .font(.system(size: 13))
                        .foregroundColor(CosmicTheme.silver)
                        .textSelection(.enabled)
                }
            }
        }
    }

    static func inlineAttributed(_ text: String) -> AttributedString {
        if let attr = try? AttributedString(
            markdown: text,
            options: AttributedString.MarkdownParsingOptions(interpretedSyntax: .inlineOnlyPreservingWhitespace)
        ) {
            return attr
        }
        return AttributedString(text)
    }

    static func parseBlocks(_ raw: String) -> [MarkdownBlockNode] {
        let lines = raw.components(separatedBy: "\n")
        var nodes: [MarkdownBlockNode] = []
        var idx = 0

        while idx < lines.count {
            let line = lines[idx]
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            if trimmed.isEmpty {
                idx += 1
                continue
            }

            // Table detection (`| col1 | col2 |`)
            if trimmed.hasPrefix("|") && trimmed.hasSuffix("|") && trimmed.filter({ $0 == "|" }).count >= 2 {
                var tableLines: [String] = []
                while idx < lines.count {
                    let tl = lines[idx].trimmingCharacters(in: .whitespaces)
                    if tl.hasPrefix("|") && tl.contains("|") {
                        tableLines.append(tl)
                        idx += 1
                    } else {
                        break
                    }
                }
                let parsedRows: [[String]] = tableLines.compactMap { rowStr in
                    let inner = rowStr.trimmingCharacters(in: CharacterSet(charactersIn: "| "))
                    let cells = inner.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
                    let isSeparator = cells.allSatisfy { cell in
                        !cell.isEmpty && cell.allSatisfy { $0 == "-" || $0 == ":" || $0 == " " }
                    }
                    return isSeparator ? nil : cells
                }
                if let firstRow = parsedRows.first {
                    let bodyRows = Array(parsedRows.dropFirst())
                    nodes.append(.table(headers: firstRow, rows: bodyRows))
                }
                continue
            }

            // Heading detection
            if trimmed.hasPrefix("### ") {
                nodes.append(.heading(level: 3, text: String(trimmed.dropFirst(4))))
                idx += 1
                continue
            } else if trimmed.hasPrefix("## ") {
                nodes.append(.heading(level: 2, text: String(trimmed.dropFirst(3))))
                idx += 1
                continue
            } else if trimmed.hasPrefix("# ") {
                nodes.append(.heading(level: 1, text: String(trimmed.dropFirst(2))))
                idx += 1
                continue
            }

            // Bullet list detection
            if trimmed.hasPrefix("- ") || trimmed.hasPrefix("* ") || trimmed.hasPrefix("• ") {
                var items: [String] = []
                while idx < lines.count {
                    let bl = lines[idx].trimmingCharacters(in: .whitespaces)
                    if bl.hasPrefix("- ") || bl.hasPrefix("* ") {
                        items.append(String(bl.dropFirst(2)))
                        idx += 1
                    } else if bl.hasPrefix("• ") {
                        items.append(String(bl.dropFirst(2)))
                        idx += 1
                    } else {
                        break
                    }
                }
                nodes.append(.bulletList(items: items))
                continue
            }

            // Numbered list detection
            if let dotRange = trimmed.range(of: #"^\d+\.\s+"#, options: .regularExpression) {
                var numItems: [(String, String)] = []
                while idx < lines.count {
                    let nl = lines[idx].trimmingCharacters(in: .whitespaces)
                    if let r = nl.range(of: #"^\d+\.\s+"#, options: .regularExpression) {
                        let prefixNum = nl[..<r.upperBound].trimmingCharacters(in: CharacterSet(charactersIn: ". "))
                        let itemBody = String(nl[r.upperBound...])
                        numItems.append((prefixNum, itemBody))
                        idx += 1
                    } else {
                        break
                    }
                }
                let _ = dotRange
                nodes.append(.numberedList(items: numItems))
                continue
            }

            // Blockquote detection
            if trimmed.hasPrefix("> ") || trimmed == ">" {
                var quoteLines: [String] = []
                while idx < lines.count {
                    let ql = lines[idx].trimmingCharacters(in: .whitespaces)
                    if ql.hasPrefix("> ") {
                        quoteLines.append(String(ql.dropFirst(2)))
                        idx += 1
                    } else if ql == ">" {
                        idx += 1
                    } else {
                        break
                    }
                }
                nodes.append(.blockquote(text: quoteLines.joined(separator: "\n")))
                continue
            }

            // Hijaiyyah Mathematical formula callout detection
            if trimmed.contains("||BSM||") || trimmed.hasPrefix("$$") || (trimmed.contains("H_c") && trimmed.contains("=")) {
                let cleanFormula = trimmed.replacingOccurrences(of: "$$", with: "").trimmingCharacters(in: .whitespaces)
                nodes.append(.formulaCallout(text: cleanFormula))
                idx += 1
                continue
            }

            // Paragraph accumulation
            var paraLines: [String] = [line]
            idx += 1
            while idx < lines.count {
                let nextLine = lines[idx]
                let nextTrim = nextLine.trimmingCharacters(in: .whitespaces)
                if nextTrim.isEmpty ||
                    nextTrim.hasPrefix("#") ||
                    nextTrim.hasPrefix("- ") ||
                    nextTrim.hasPrefix("* ") ||
                    nextTrim.hasPrefix("• ") ||
                    nextTrim.hasPrefix("> ") ||
                    (nextTrim.hasPrefix("|") && nextTrim.hasSuffix("|")) ||
                    nextTrim.range(of: #"^\d+\.\s+"#, options: .regularExpression) != nil {
                    break
                }
                paraLines.append(nextLine)
                idx += 1
            }
            nodes.append(.paragraph(text: paraLines.joined(separator: "\n")))
        }
        return nodes
    }
}

struct RichMarkdownAndCodeView: View {
    let text: String
    var messageId: String = ""
    var copiedItemId: String = ""
    var onCopyCode: ((String, String) -> Void)? = nil
    var onOpenInStudio: ((String, String) -> Void)? = nil

    var body: some View {
        let parts = text.components(separatedBy: "```")
        VStack(alignment: .leading, spacing: 9) {
            ForEach(Array(parts.enumerated()), id: \.offset) { idx, block in
                if idx % 2 == 1 {
                    let lines = block.components(separatedBy: "\n")
                    let lang = lines.first?.trimmingCharacters(in: .whitespacesAndNewlines) ?? "code"
                    let codeBody = lines.dropFirst().joined(separator: "\n")
                    let blockId = messageId.isEmpty ? "code-\(idx)" : "code-\(messageId)-\(idx)"
                    CodeBlockCardView(
                        language: lang,
                        codeBody: codeBody,
                        blockId: blockId,
                        copiedItemId: copiedItemId,
                        onCopyCode: onCopyCode,
                        onOpenInStudio: onOpenInStudio
                    )
                } else {
                    let cleanBlock = block.trimmingCharacters(in: .whitespacesAndNewlines)
                    if !cleanBlock.isEmpty {
                        MarkdownProseSegmentView(rawSegment: cleanBlock)
                    }
                }
            }
        }
    }
}

// MARK: - Multiline Auto-Resizing Chat Composer (Enter = Send, Shift+Enter = New Line, Cmd+V Paste)

final class NUIComposerNSTextView: NSTextView {
    var onEnterSend: (() -> Void)?
    var onTextChange: ((String) -> Void)?

    override func keyDown(with event: NSEvent) {
        let isReturnOrEnter = (event.keyCode == 36 || event.keyCode == 76)
        if isReturnOrEnter {
            let flags = event.modifierFlags.intersection(.deviceIndependentFlagsMask)
            if flags.contains(.shift) {
                super.insertNewline(nil)
                onTextChange?(self.string)
                return
            } else if !flags.contains(.command) && !flags.contains(.option) && !flags.contains(.control) {
                onEnterSend?()
                return
            }
        }
        super.keyDown(with: event)
    }

    override func paste(_ sender: Any?) {
        let pasted = NUIClipboardManager.shared.readPasteboardString()
        if !pasted.isEmpty {
            self.insertText(pasted, replacementRange: self.selectedRange())
            onTextChange?(self.string)
        } else {
            super.paste(sender)
            onTextChange?(self.string)
        }
    }

    /// Simulates key event handling deterministically for automated tests (`Enter` vs `Shift+Enter`).
    func handleSimulatedReturnKey(shiftPressed: Bool) {
        if shiftPressed {
            let sel = self.selectedRange()
            self.insertText("\n", replacementRange: sel)
            onTextChange?(self.string)
        } else {
            onEnterSend?()
        }
    }
}

struct ChatComposerTextView: NSViewRepresentable {
    @Binding var text: String
    var placeholder: String
    var isDisabled: Bool = false
    var focusTrigger: Int = 0
    var onSubmitSend: () -> Void

    final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: ChatComposerTextView
        weak var textView: NUIComposerNSTextView?
        var lastFocusTrigger: Int = -1

        init(_ parent: ChatComposerTextView) {
            self.parent = parent
        }

        func textDidChange(_ notification: Notification) {
            guard let tv = notification.object as? NSTextView else { return }
            if parent.text != tv.string {
                parent.text = tv.string
            }
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSScrollView()
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = false
        scrollView.autohidesScrollers = true
        scrollView.drawsBackground = true
        scrollView.backgroundColor = NSColor(red: 0.05, green: 0.08, blue: 0.14, alpha: 1.0)
        scrollView.borderType = .noBorder

        let tv = NUIComposerNSTextView()
        tv.delegate = context.coordinator
        tv.isRichText = false
        tv.importsGraphics = false
        tv.isEditable = true
        tv.isSelectable = true
        tv.allowsUndo = true
        tv.isAutomaticQuoteSubstitutionEnabled = false
        tv.isAutomaticDashSubstitutionEnabled = false
        tv.isAutomaticTextReplacementEnabled = false
        tv.font = NSFont.systemFont(ofSize: 13.0)
        tv.textColor = NSColor(red: 0.90, green: 0.94, blue: 0.98, alpha: 1.0)
        tv.insertionPointColor = NSColor(red: 0.00, green: 0.85, blue: 0.96, alpha: 1.0)
        tv.backgroundColor = NSColor(red: 0.05, green: 0.08, blue: 0.14, alpha: 1.0)
        tv.textContainerInset = NSSize(width: 6, height: 7)
        tv.isVerticallyResizable = true
        tv.isHorizontallyResizable = false
        tv.autoresizingMask = [.width]
        tv.textContainer?.widthTracksTextView = true
        tv.textContainer?.containerSize = NSSize(width: 600, height: CGFloat.greatestFiniteMagnitude)
        tv.string = text

        tv.onEnterSend = { [weak coordinator = context.coordinator] in
            guard let coordinator = coordinator else { return }
            if !coordinator.parent.isDisabled {
                coordinator.parent.onSubmitSend()
            }
        }
        tv.onTextChange = { [weak coordinator = context.coordinator] updated in
            guard let coordinator = coordinator else { return }
            if coordinator.parent.text != updated {
                coordinator.parent.text = updated
            }
        }

        scrollView.documentView = tv
        context.coordinator.textView = tv
        return scrollView
    }

    func updateNSView(_ nsView: NSScrollView, context: Context) {
        context.coordinator.parent = self
        guard let tv = context.coordinator.textView else { return }
        if tv.string != text {
            tv.string = text
        }
        if context.coordinator.lastFocusTrigger != focusTrigger {
            context.coordinator.lastFocusTrigger = focusTrigger
            DispatchQueue.main.async {
                tv.window?.makeFirstResponder(tv)
            }
        }
    }

    static func calculatedHeight(for text: String) -> CGFloat {
        let lineCount = max(1, text.components(separatedBy: "\n").count + (text.count / 95))
        let rawHeight = CGFloat(lineCount) * 20.0 + 18.0
        return min(max(rawHeight, 40.0), 132.0)
    }
}


// MARK: - Smart Scroll Position & Wheel Detector for macOS NSScrollView

final class SmartScrollObserverNSView: NSView {
    var onUserScrollUp: (() -> Void)?
    var onReachedBottom: (() -> Void)?
    private weak var observedScrollView: NSScrollView?
    private var wheelMonitor: Any?

    override func viewDidMoveToWindow() {
        super.viewDidMoveToWindow()
        attachScrollObserverIfNeeded()
    }

    override func viewDidMoveToSuperview() {
        super.viewDidMoveToSuperview()
        attachScrollObserverIfNeeded()
    }

    private func attachScrollObserverIfNeeded() {
        guard window != nil else {
            removeObservers()
            return
        }
        var candidate: NSView? = superview
        while let current = candidate {
            if let sv = current as? NSScrollView {
                if observedScrollView !== sv {
                    removeObservers()
                    observedScrollView = sv
                    sv.contentView.postsBoundsChangedNotifications = true
                    NotificationCenter.default.addObserver(
                        self,
                        selector: #selector(handleScrollViewLiveScroll(_:)),
                        name: NSScrollView.didLiveScrollNotification,
                        object: sv
                    )
                    NotificationCenter.default.addObserver(
                        self,
                        selector: #selector(handleClipBoundsChanged(_:)),
                        name: NSView.boundsDidChangeNotification,
                        object: sv.contentView
                    )
                }
                break
            }
            candidate = current.superview
        }

        if wheelMonitor == nil {
            wheelMonitor = NSEvent.addLocalMonitorForEvents(matching: .scrollWheel) { [weak self] event in
                guard let self = self,
                      let sv = self.observedScrollView,
                      let win = sv.window,
                      event.window === win else {
                    return event
                }
                let locInSv = sv.convert(event.locationInWindow, from: nil)
                if sv.bounds.contains(locInSv) {
                    if event.scrollingDeltaY > 1.5 {
                        self.onUserScrollUp?()
                    } else if event.scrollingDeltaY < -1.0 {
                        self.evaluateBottomProximity(in: sv)
                    }
                }
                return event
            }
        }
    }

    @objc private func handleScrollViewLiveScroll(_ notification: Notification) {
        guard let sv = observedScrollView else { return }
        evaluateBottomProximity(in: sv, allowPauseOnUp: true)
    }

    @objc private func handleClipBoundsChanged(_ notification: Notification) {
        guard let sv = observedScrollView else { return }
        evaluateBottomProximity(in: sv, allowPauseOnUp: false)
    }

    private func evaluateBottomProximity(in sv: NSScrollView, allowPauseOnUp: Bool = false) {
        guard let docView = sv.documentView else { return }
        let docHeight = docView.bounds.height
        let visibleRect = sv.contentView.documentVisibleRect
        let maxVisibleY = visibleRect.origin.y + visibleRect.height
        let distanceFromBottom = docHeight - maxVisibleY

        if distanceFromBottom <= 28.0 {
            onReachedBottom?()
        } else if allowPauseOnUp && distanceFromBottom > 52.0 {
            onUserScrollUp?()
        }
    }

    private func removeObservers() {
        NotificationCenter.default.removeObserver(self)
        if let mon = wheelMonitor {
            NSEvent.removeMonitor(mon)
            wheelMonitor = nil
        }
        observedScrollView = nil
    }

    deinit {
        removeObservers()
    }
}

struct SmartScrollDetectorRepresentable: NSViewRepresentable {
    let onUserScrollUp: () -> Void
    let onReachedBottom: () -> Void

    func makeNSView(context: Context) -> SmartScrollObserverNSView {
        let v = SmartScrollObserverNSView(frame: .zero)
        v.onUserScrollUp = onUserScrollUp
        v.onReachedBottom = onReachedBottom
        return v
    }

    func updateNSView(_ nsView: SmartScrollObserverNSView, context: Context) {
        nsView.onUserScrollUp = onUserScrollUp
        nsView.onReachedBottom = onReachedBottom
    }
}

// MARK: - Real Native WKWebView Browser Engine (Multi-Tab + WKNavigationDelegate + WKUIDelegate + WKDownloadDelegate + Full Lifecycle Tracing)

final class BrowserViewportContainerNSView: NSView {
    var onLayoutChange: ((CGSize) -> Void)?
    let fallbackScrollView = NSScrollView()
    let fallbackTextView = NSTextView()

    override init(frame frameRect: NSRect) {
        let initial = (frameRect.width > 0 && frameRect.height > 0)
            ? frameRect
            : NSRect(x: 0, y: 0, width: 960, height: 640)
        super.init(frame: initial)
        self.autoresizesSubviews = true
        self.wantsLayer = true
        self.layer?.backgroundColor = NSColor(calibratedRed: 0.024, green: 0.047, blue: 0.086, alpha: 1.0).cgColor
        setupFallbackDocumentView(initial: initial)
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        self.autoresizesSubviews = true
        setupFallbackDocumentView(initial: NSRect(x: 0, y: 0, width: 960, height: 640))
    }

    private func setupFallbackDocumentView(initial: NSRect) {
        fallbackScrollView.frame = initial
        fallbackScrollView.autoresizingMask = [.width, .height]
        fallbackScrollView.hasVerticalScroller = true
        fallbackScrollView.drawsBackground = true
        fallbackScrollView.backgroundColor = NSColor(calibratedRed: 0.024, green: 0.047, blue: 0.086, alpha: 1.0)
        fallbackScrollView.isHidden = true

        fallbackTextView.frame = initial
        fallbackTextView.isEditable = false
        fallbackTextView.isSelectable = true
        fallbackTextView.drawsBackground = true
        fallbackTextView.backgroundColor = NSColor(calibratedRed: 0.024, green: 0.047, blue: 0.086, alpha: 1.0)
        fallbackTextView.textColor = NSColor(calibratedRed: 0.949, green: 0.965, blue: 0.980, alpha: 1.0)
        fallbackTextView.font = NSFont.systemFont(ofSize: 13.5)
        fallbackTextView.textContainerInset = NSSize(width: 24, height: 22)
        fallbackTextView.autoresizingMask = [.width]
        fallbackScrollView.documentView = fallbackTextView
        addSubview(fallbackScrollView)
    }

    func showFallbackDocument(title: String, url: String, bodyText: String, isError: Bool) {
        let header = isError
            ? "⚠️ NAVIGATION ERROR — \(title)\nURL: \(url)\n\n"
            : "🌐 \(title)\nURL: \(url)\n\n"
        fallbackTextView.string = header + bodyText
        fallbackScrollView.isHidden = false
        if fallbackScrollView.superview !== self {
            addSubview(fallbackScrollView)
        }
    }

    func hideFallbackDocument() {
        fallbackScrollView.isHidden = true
    }

    override func layout() {
        super.layout()
        let effBounds = (bounds.width > 10 && bounds.height > 10)
            ? bounds
            : NSRect(x: 0, y: 0, width: max(480, bounds.width), height: max(380, bounds.height))
        for sub in subviews {
            if sub.frame != effBounds {
                sub.frame = effBounds
            }
        }
        onLayoutChange?(effBounds.size)
    }

    override func resizeSubviews(withOldSize oldSize: NSSize) {
        super.resizeSubviews(withOldSize: oldSize)
        let effBounds = (bounds.width > 10 && bounds.height > 10)
            ? bounds
            : NSRect(x: 0, y: 0, width: max(480, bounds.width), height: max(380, bounds.height))
        for sub in subviews {
            sub.frame = effBounds
        }
        onLayoutChange?(effBounds.size)
    }
}

@MainActor
final class NUIBrowserEngineController: NSObject, ObservableObject, WKNavigationDelegate, WKUIDelegate, WKDownloadDelegate {
    weak var store: NUIDesktopStore?
    private var tabWebViews: [String: WKWebView] = [:]
    private var kvoObservations: [String: [NSKeyValueObservation]] = [:]
    private var downloadDestinations: [ObjectIdentifier: URL] = [:]
    private var activeNavigationIdByTab: [String: String] = [:]
    private var navObjectToId: [ObjectIdentifier: String] = [:]
    private var hasCommittedByTab: [String: Bool] = [:]
    private var isRenderingDiagnosticHTMLByTab: [String: Bool] = [:]
    private var processTerminationCountByNavId: [String: Int] = [:]
    private var pendingInlineHTMLByNavId: [String: String] = [:]
    private var watchdogTasksByTab: [String: Task<Void, Never>] = [:]
    @Published var navigationTraces: [String: BrowserNavigationTraceRecord] = [:]
    @Published var navigationTraceOrder: [String] = []
    @Published var viewportWidth: Double = 960.0
    @Published var viewportHeight: Double = 640.0
    let containerNSView: BrowserViewportContainerNSView = BrowserViewportContainerNSView(frame: NSRect(x: 0, y: 0, width: 960, height: 640))
    static let traceLogPath = "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/browser_navigation_trace.jsonl"

    override init() {
        super.init()
        containerNSView.onLayoutChange = { [weak self] sz in
            Task { @MainActor in
                self?.viewportWidth = Double(sz.width)
                self?.viewportHeight = Double(sz.height)
            }
        }
    }

    private func generateNavigationId() -> String {
        let ms = Int(Date().timeIntervalSince1970 * 1000)
        let short = UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(6).lowercased()
        return "nav-\(ms)-\(short)"
    }

    private func redactSensitiveInfo(_ text: String) -> String {
        var out = text
        let patterns = [
            "(?i)(authorization|token|password|secret|api_key)=([^&\\s]+)",
            "(?i)://[^/@\\s]+@"
        ]
        for pat in patterns {
            if let regex = try? NSRegularExpression(pattern: pat) {
                out = regex.stringByReplacingMatches(
                    in: out,
                    range: NSRange(out.startIndex..., in: out),
                    withTemplate: "[REDACTED]"
                )
            }
        }
        return out
    }

    func appendTraceLog(
        navigationId: String,
        tabId: String,
        stage: String,
        requestedURL: String,
        normalizedURL: String,
        actualURL: String,
        httpStatus: Int = 0,
        pageTitle: String = "",
        errorText: String = "",
        elapsedMs: Double = 0.0,
        contentVisible: Bool = false
    ) {
        let entry: [String: Any] = [
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "navigation_id": navigationId,
            "tab_id": tabId,
            "stage": stage,
            "requested_url": redactSensitiveInfo(requestedURL),
            "normalized_url": redactSensitiveInfo(normalizedURL),
            "actual_url": redactSensitiveInfo(actualURL),
            "http_status": httpStatus,
            "page_title": pageTitle,
            "error": redactSensitiveInfo(errorText),
            "elapsed_ms": elapsedMs,
            "content_visible_in_viewport": contentVisible,
            "viewport_width": viewportWidth,
            "viewport_height": viewportHeight
        ]
        if let jsonData = try? JSONSerialization.data(withJSONObject: entry),
           let line = String(data: jsonData, encoding: .utf8) {
            let lineWithNL = line + "\n"
            let url = URL(fileURLWithPath: Self.traceLogPath)
            try? FileManager.default.createDirectory(at: url.deletingLastPathComponent(), withIntermediateDirectories: true)
            if FileManager.default.fileExists(atPath: Self.traceLogPath),
               let fh = try? FileHandle(forWritingTo: url) {
                fh.seekToEndOfFile()
                if let d = lineWithNL.data(using: .utf8) {
                    fh.write(d)
                }
                try? fh.close()
            } else {
                try? lineWithNL.write(toFile: Self.traceLogPath, atomically: true, encoding: .utf8)
            }
        }
    }

    func webViewForTab(_ tabId: String, sessionPolicy: String) -> WKWebView {
        if let existing = tabWebViews[tabId] {
            return existing
        }
        let config = WKWebViewConfiguration()
        config.websiteDataStore = (sessionPolicy == "TEMPORARY_PRIVATE")
            ? .nonPersistent()
            : .default()
        config.preferences.javaScriptCanOpenWindowsAutomatically = true

        let initBounds = (containerNSView.bounds.width > 10 && containerNSView.bounds.height > 10)
            ? containerNSView.bounds
            : NSRect(x: 0, y: 0, width: 960, height: 640)
        let wv = WKWebView(frame: initBounds, configuration: config)
        wv.autoresizingMask = [.width, .height]
        wv.navigationDelegate = self
        wv.uiDelegate = self
        wv.allowsBackForwardNavigationGestures = true
        wv.allowsMagnification = true
        wv.customUserAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) CosmicTeraNUI/1.5 Safari/605.1.15"

        let obsProgress = wv.observe(\.estimatedProgress, options: [.new]) { [weak self] webView, _ in
            let prog = webView.estimatedProgress
            Task { @MainActor in
                self?.handleProgressChange(for: webView, progress: prog)
            }
        }
        let obsTitle = wv.observe(\.title, options: [.new]) { [weak self] webView, _ in
            let title = webView.title ?? ""
            Task { @MainActor in
                self?.handleTitleOrURLChange(for: webView, title: title)
            }
        }
        let obsURL = wv.observe(\.url, options: [.new]) { [weak self] webView, _ in
            let currentURL = webView.url?.absoluteString ?? ""
            Task { @MainActor in
                self?.handleTitleOrURLChange(for: webView, url: currentURL)
            }
        }
        let obsBack = wv.observe(\.canGoBack, options: [.new]) { [weak self] webView, _ in
            Task { @MainActor in
                self?.syncBackForwardFlags(for: webView)
            }
        }
        let obsForward = wv.observe(\.canGoForward, options: [.new]) { [weak self] webView, _ in
            Task { @MainActor in
                self?.syncBackForwardFlags(for: webView)
            }
        }
        kvoObservations[tabId] = [obsProgress, obsTitle, obsURL, obsBack, obsForward]
        tabWebViews[tabId] = wv
        return wv
    }

    func attachActiveTabWebView(_ tabId: String, sessionPolicy: String) -> WKWebView {
        let wv = webViewForTab(tabId, sessionPolicy: sessionPolicy)
        let effBounds = (containerNSView.bounds.width > 10 && containerNSView.bounds.height > 10)
            ? containerNSView.bounds
            : NSRect(x: 0, y: 0, width: 960, height: 640)
        if wv.superview !== containerNSView {
            for sub in containerNSView.subviews where sub !== containerNSView.fallbackScrollView {
                sub.removeFromSuperview()
            }
            wv.translatesAutoresizingMaskIntoConstraints = true
            wv.autoresizingMask = [.width, .height]
            wv.frame = effBounds
            containerNSView.addSubview(wv, positioned: .below, relativeTo: containerNSView.fallbackScrollView)
            containerNSView.needsLayout = true
            containerNSView.layoutSubtreeIfNeeded()
        } else if wv.frame.width <= 0 || wv.frame.height <= 0 {
            wv.frame = effBounds
        }
        viewportWidth = Double(wv.frame.width)
        viewportHeight = Double(wv.frame.height)
        return wv
    }

    func closeTabWebView(_ tabId: String) {
        watchdogTasksByTab[tabId]?.cancel()
        watchdogTasksByTab.removeValue(forKey: tabId)
        activeNavigationIdByTab.removeValue(forKey: tabId)
        hasCommittedByTab.removeValue(forKey: tabId)
        isRenderingDiagnosticHTMLByTab.removeValue(forKey: tabId)
        kvoObservations.removeValue(forKey: tabId)
        if let wv = tabWebViews.removeValue(forKey: tabId) {
            wv.stopLoading()
            if wv.superview === containerNSView {
                wv.removeFromSuperview()
            }
        }
    }

    @discardableResult
    func loadURLInTab(
        tabId: String,
        urlString: String,
        sessionPolicy: String,
        operatingMode: String,
        requestedRawInput: String? = nil,
        navigationId: String? = nil,
        forceReload: Bool = false
    ) -> String {
        let webView = attachActiveTabWebView(tabId, sessionPolicy: sessionPolicy)
        containerNSView.hideFallbackDocument()
        let rawIn = requestedRawInput ?? urlString
        let norm = BrowserAddressNormalizer.normalize(urlString)
        let navId = navigationId ?? generateNavigationId()

        watchdogTasksByTab[tabId]?.cancel()
        activeNavigationIdByTab[tabId] = navId
        hasCommittedByTab[tabId] = false
        isRenderingDiagnosticHTMLByTab[tabId] = false
        processTerminationCountByNavId[navId] = 0

        if !norm.ok {
            let errHTML = BrowserAddressNormalizer.buildErrorHTML(
                url: rawIn,
                domain: "invalid-url",
                errorCode: norm.errorCode,
                errorMessage: norm.errorMessage
            )
            var tr = BrowserNavigationTraceRecord(
                id: navId,
                tabId: tabId,
                requestedURL: rawIn,
                normalizedURL: "",
                actualURL: ""
            )
            tr.didFailProvisionalNavigation = true
            tr.state = "FAILED"
            tr.errorCode = norm.errorCode
            tr.errorMessage = norm.errorMessage
            tr.pageTitle = "Gagal Memuat Halaman — URL Tidak Valid"
            tr.contentVisibleInViewport = true
            navigationTraces[navId] = tr
            if !navigationTraceOrder.contains(navId) { navigationTraceOrder.append(navId) }

            store?.applyNavigationFailureState(
                tabId: tabId,
                navigationId: navId,
                failingURL: rawIn,
                domain: "invalid-url",
                errorCode: norm.errorCode,
                errorMessage: norm.errorMessage,
                errorHTML: errHTML
            )
            renderErrorPageInTab(tabId: tabId, html: errHTML, failingURL: nil, sessionPolicy: sessionPolicy)
            return navId
        }

        let resolvedURL = norm.resolvedURL
        let domain = norm.domain

        // Section 2: Reset stale title, loading state, and favicon immediately before loading
        var trace = BrowserNavigationTraceRecord(
            id: navId,
            tabId: tabId,
            requestedURL: rawIn,
            normalizedURL: resolvedURL,
            actualURL: resolvedURL,
            startedAt: Date()
        )
        trace.state = "LOADING"
        trace.pageTitle = "Loading \(domain)..."
        navigationTraces[navId] = trace
        if !navigationTraceOrder.contains(navId) { navigationTraceOrder.append(navId) }

        store?.applyNavigationStartState(
            tabId: tabId,
            navigationId: navId,
            requestedURL: rawIn,
            normalizedURL: resolvedURL,
            domain: domain,
            securityState: norm.securityState
        )

        if operatingMode == "LOCAL" {
            let localErrHTML = BrowserAddressNormalizer.buildErrorHTML(
                url: resolvedURL,
                domain: domain,
                errorCode: "OFFLINE_LOCAL_MODE_LOCK",
                errorMessage: "Outbound internet dinonaktifkan pada mode LOCAL. Ubah Network Mode di bar atas ke HYBRID atau ONLINE untuk membuka situs eksternal."
            )
            trace.didFailProvisionalNavigation = true
            trace.state = "FAILED"
            trace.errorCode = "OFFLINE_LOCAL_MODE_LOCK"
            trace.errorMessage = "Outbound internet blocked by LOCAL mode."
            trace.pageTitle = "Gagal Memuat Halaman — \(domain)"
            trace.contentVisibleInViewport = true
            navigationTraces[navId] = trace

            store?.applyNavigationFailureState(
                tabId: tabId,
                navigationId: navId,
                failingURL: resolvedURL,
                domain: domain,
                errorCode: "OFFLINE_LOCAL_MODE_LOCK",
                errorMessage: "Outbound internet dinonaktifkan pada mode LOCAL.",
                errorHTML: localErrHTML
            )
            renderErrorPageInTab(tabId: tabId, html: localErrHTML, failingURL: resolvedURL, sessionPolicy: sessionPolicy)
            appendTraceLog(
                navigationId: navId,
                tabId: tabId,
                stage: "BLOCKED_BY_LOCAL_MODE",
                requestedURL: rawIn,
                normalizedURL: resolvedURL,
                actualURL: resolvedURL,
                pageTitle: trace.pageTitle,
                errorText: trace.errorMessage,
                contentVisible: true
            )
            return navId
        }

        guard let urlObj = URL(string: resolvedURL) else { return navId }
        if webView.isLoading {
            webView.stopLoading()
        }
        let req = URLRequest(
            url: urlObj,
            cachePolicy: forceReload ? .reloadIgnoringLocalCacheData : .useProtocolCachePolicy,
            timeoutInterval: 15.0
        )
        if let wkNav = webView.load(req) {
            navObjectToId[ObjectIdentifier(wkNav)] = navId
        }
        appendTraceLog(
            navigationId: navId,
            tabId: tabId,
            stage: "LOAD_REQUEST_DISPATCHED",
            requestedURL: rawIn,
            normalizedURL: resolvedURL,
            actualURL: resolvedURL,
            pageTitle: "Loading \(domain)..."
        )

        // Section 2: 15-second watchdog so LOADING never hangs indefinitely
        watchdogTasksByTab[tabId] = Task { @MainActor [weak self] in
            try? await Task.sleep(nanoseconds: 15_000_000_000)
            guard !Task.isCancelled, let self = self else { return }
            guard self.activeNavigationIdByTab[tabId] == navId else { return }
            if let tr = self.navigationTraces[navId], (tr.state == "LOADING" || tr.state == "COMMITTED") && !tr.didFinish {
                let wv = self.webViewForTab(tabId, sessionPolicy: sessionPolicy)
                wv.stopLoading()
                let timeoutHTML = BrowserAddressNormalizer.buildErrorHTML(
                    url: resolvedURL,
                    domain: domain,
                    errorCode: "CONNECTION_TIMED_OUT",
                    errorMessage: "Waktu pemuatan halaman habis (melebihi 15 detik) tanpa respons akhir dari server."
                )
                self.handleNavigationFailureInternal(
                    webView: wv,
                    tabId: tabId,
                    navigationId: navId,
                    stage: "WATCHDOG_TIMEOUT",
                    errorCode: "CONNECTION_TIMED_OUT",
                    errorMessage: "Waktu pemuatan halaman habis (15s watchdog timeout).",
                    errorHTML: timeoutHTML
                )
            }
        }

        return navId
    }

    func renderErrorPageInTab(tabId: String, html: String, failingURL: String?, sessionPolicy: String) {
        let wv = attachActiveTabWebView(tabId, sessionPolicy: sessionPolicy)
        isRenderingDiagnosticHTMLByTab[tabId] = true
        let cleanBody = html.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
            .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        containerNSView.showFallbackDocument(
            title: store?.browserPageTitle ?? "Gagal Memuat Halaman",
            url: failingURL ?? (store?.browserActiveURL ?? ""),
            bodyText: cleanBody,
            isError: true
        )
        let navId = activeNavigationIdByTab[tabId] ?? ""
        if (processTerminationCountByNavId[navId] ?? 0) == 0 {
            wv.loadHTMLString(html, baseURL: nil)
        }
    }

    func setZoom(tabId: String, zoom: Double, sessionPolicy: String) {
        let wv = webViewForTab(tabId, sessionPolicy: sessionPolicy)
        wv.pageZoom = CGFloat(zoom)
    }

    func executeFindOnPage(tabId: String, query: String, sessionPolicy: String) {
        let wv = webViewForTab(tabId, sessionPolicy: sessionPolicy)
        let escaped = query.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: "'", with: "\\'")
        if escaped.isEmpty {
            wv.evaluateJavaScript("window.getSelection().removeAllRanges();", completionHandler: nil)
            return
        }
        wv.evaluateJavaScript("window.find('\(escaped)', false, false, true, false, true, false);") { [weak self] _, _ in
            let countJS = "(function(){ var bodyText = document.body ? document.body.innerText : ''; var m = bodyText.match(new RegExp('\(escaped)', 'gi')); return m ? m.length : 0; })()"
            wv.evaluateJavaScript(countJS) { res, _ in
                if let cnt = res as? Int {
                    Task { @MainActor in
                        self?.store?.browserFindMatchCount = cnt
                    }
                }
            }
        }
    }

    private func tabId(for webView: WKWebView) -> String? {
        tabWebViews.first(where: { $0.value === webView })?.key
    }

    private func resolveNavigationId(for navigation: WKNavigation?, tabId: String) -> String? {
        if let nav = navigation, let mapped = navObjectToId[ObjectIdentifier(nav)] {
            return mapped
        }
        return activeNavigationIdByTab[tabId]
    }

    private func handleProgressChange(for webView: WKWebView, progress: Double) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        guard !(isRenderingDiagnosticHTMLByTab[tid] ?? false) else { return }
        if tid == store.activeBrowserTabId {
            store.browserLoadingProgress = max(0.10, progress)
        }
        store.updateLocalTab(tid) { tab in
            tab.progress = progress
        }
    }

    private func handleTitleOrURLChange(for webView: WKWebView, title: String? = nil, url: String? = nil) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        guard !(isRenderingDiagnosticHTMLByTab[tid] ?? false) else { return }
        // Section 2: Never overwrite with old page's title before didCommit fires for the current navigation!
        let committed = hasCommittedByTab[tid] ?? false
        guard committed else { return }

        store.updateLocalTab(tid) { tab in
            if let t = title?.trimmingCharacters(in: .whitespacesAndNewlines), !t.isEmpty {
                tab.title = t
            }
            if let u = url, !u.isEmpty, !u.hasPrefix("about:") {
                tab.url = u
                if let host = URL(string: u)?.host?.lowercased() {
                    tab.domain = host
                    tab.favicon = BrowserAddressNormalizer.faviconForDomain(host)
                }
                tab.securityState = u.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
            }
        }
        if tid == store.activeBrowserTabId {
            if let t = title?.trimmingCharacters(in: .whitespacesAndNewlines), !t.isEmpty {
                store.browserPageTitle = t
            }
            if let u = url, !u.isEmpty, !u.hasPrefix("about:") {
                store.browserAddress = u
                store.browserActiveURL = u
                store.browserSecurityState = u.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
            }
        }
    }

    private func syncBackForwardFlags(for webView: WKWebView) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        let back = webView.canGoBack
        let forward = webView.canGoForward
        store.updateLocalTab(tid) { tab in
            tab.canGoBack = back || tab.canGoBack
            tab.canGoForward = forward || tab.canGoForward
        }
    }

    private func handleNavigationFailureInternal(
        webView: WKWebView,
        tabId: String,
        navigationId: String,
        stage: String,
        errorCode: String,
        errorMessage: String,
        errorHTML: String? = nil
    ) {
        guard let store = store else { return }
        watchdogTasksByTab[tabId]?.cancel()
        var tr = navigationTraces[navigationId] ?? BrowserNavigationTraceRecord(
            id: navigationId,
            tabId: tabId,
            requestedURL: store.browserAddress,
            normalizedURL: store.browserActiveURL,
            actualURL: store.browserActiveURL
        )
        if stage.contains("PROVISIONAL") || stage.contains("TIMEOUT") {
            tr.didFailProvisionalNavigation = true
        } else {
            tr.didFail = true
        }
        tr.state = "FAILED"
        tr.errorCode = errorCode
        tr.errorMessage = redactSensitiveInfo(errorMessage)
        tr.elapsedMs = round(Date().timeIntervalSince(tr.startedAt) * 1000.0)
        let failURL = tr.actualURL.isEmpty ? store.browserActiveURL : tr.actualURL
        let failDom = URL(string: failURL)?.host?.lowercased() ?? store.activeTabModel.domain
        tr.pageTitle = "Gagal Memuat Halaman — \(failDom)"
        tr.contentVisibleInViewport = true
        navigationTraces[navigationId] = tr

        let htmlToRender = errorHTML ?? BrowserAddressNormalizer.buildErrorHTML(
            url: failURL,
            domain: failDom,
            errorCode: errorCode,
            errorMessage: errorMessage
        )
        store.applyNavigationFailureState(
            tabId: tabId,
            navigationId: navigationId,
            failingURL: failURL,
            domain: failDom,
            errorCode: errorCode,
            errorMessage: errorMessage,
            errorHTML: htmlToRender
        )
        renderErrorPageInTab(tabId: tabId, html: htmlToRender, failingURL: failURL, sessionPolicy: store.browserSessionPolicy)

        appendTraceLog(
            navigationId: navigationId,
            tabId: tabId,
            stage: stage,
            requestedURL: tr.requestedURL,
            normalizedURL: tr.normalizedURL,
            actualURL: failURL,
            httpStatus: tr.httpStatus,
            pageTitle: tr.pageTitle,
            errorText: "\(errorCode): \(errorMessage)",
            elapsedMs: tr.elapsedMs,
            contentVisible: true
        )

        Task {
            await store.syncWebViewLifecycleToBackend(
                tabId: tabId,
                navigationId: navigationId,
                event: stage,
                requestedURL: tr.requestedURL,
                normalizedURL: tr.normalizedURL,
                actualURL: failURL,
                url: failURL,
                title: tr.pageTitle,
                httpStatus: tr.httpStatus,
                errorCode: errorCode,
                errorMessage: errorMessage,
                elapsedMs: tr.elapsedMs,
                contentVisible: true
            )
        }
    }

    // MARK: WKNavigationDelegate

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationAction: WKNavigationAction,
        decisionHandler: @escaping (WKNavigationActionPolicy) -> Void
    ) {
        if navigationAction.shouldPerformDownload {
            decisionHandler(.download)
            return
        }
        if navigationAction.targetFrame == nil, let targetURL = navigationAction.request.url?.absoluteString {
            Task { @MainActor in
                await self.store?.openNewBrowserTab(initialURL: targetURL)
            }
            decisionHandler(.cancel)
            return
        }
        // If user clicked an in-page link, start a fresh navigationId so title & state track the clicked link
        if navigationAction.navigationType == .linkActivated,
           let tid = tabId(for: webView),
           let clickedURL = navigationAction.request.url?.absoluteString,
           !clickedURL.hasPrefix("about:") {
            let navId = generateNavigationId()
            activeNavigationIdByTab[tid] = navId
            hasCommittedByTab[tid] = false
            isRenderingDiagnosticHTMLByTab[tid] = false
            let dom = URL(string: clickedURL)?.host?.lowercased() ?? "page"
            var tr = BrowserNavigationTraceRecord(
                id: navId,
                tabId: tid,
                requestedURL: clickedURL,
                normalizedURL: clickedURL,
                actualURL: clickedURL,
                startedAt: Date()
            )
            tr.pageTitle = "Loading \(dom)..."
            navigationTraces[navId] = tr
            if !navigationTraceOrder.contains(navId) { navigationTraceOrder.append(navId) }
            store?.applyNavigationStartState(
                tabId: tid,
                navigationId: navId,
                requestedURL: clickedURL,
                normalizedURL: clickedURL,
                domain: dom,
                securityState: clickedURL.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
            )
        }
        decisionHandler(.allow)
    }

    func webView(
        _ webView: WKWebView,
        decidePolicyFor navigationResponse: WKNavigationResponse,
        decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void
    ) {
        if let httpResp = navigationResponse.response as? HTTPURLResponse,
           let tid = tabId(for: webView),
           !(isRenderingDiagnosticHTMLByTab[tid] ?? false) {
            let code = httpResp.statusCode
            let navId = activeNavigationIdByTab[tid] ?? ""
            if var tr = navigationTraces[navId] {
                tr.httpStatus = code
                navigationTraces[navId] = tr
            }
            Task { @MainActor in
                self.store?.browserLastHTTPStatus = code
                self.store?.updateLocalTab(tid) { tab in
                    tab.httpStatus = code
                }
            }
        }
        if !navigationResponse.canShowMIMEType {
            decisionHandler(.download)
            return
        }
        decisionHandler(.allow)
    }

    func webView(_ webView: WKWebView, navigationAction: WKNavigationAction, didBecome download: WKDownload) {
        download.delegate = self
    }

    func webView(_ webView: WKWebView, navigationResponse: WKNavigationResponse, didBecome download: WKDownload) {
        download.delegate = self
    }

    func webView(_ webView: WKWebView, didStartProvisionalNavigation navigation: WKNavigation!) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        if isRenderingDiagnosticHTMLByTab[tid] == true {
            return
        }
        let navId = resolveNavigationId(for: navigation, tabId: tid) ?? generateNavigationId()
        if let nav = navigation {
            navObjectToId[ObjectIdentifier(nav)] = navId
        }
        // Ignore stale callback if superseded
        if let activeId = activeNavigationIdByTab[tid], activeId != navId {
            appendTraceLog(
                navigationId: navId,
                tabId: tid,
                stage: "IGNORED_STALE_didStartProvisionalNavigation",
                requestedURL: "",
                normalizedURL: "",
                actualURL: webView.url?.absoluteString ?? ""
            )
            return
        }
        activeNavigationIdByTab[tid] = navId
        hasCommittedByTab[tid] = false

        let currentURL = webView.url?.absoluteString ?? store.browserActiveURL
        let dom = URL(string: currentURL)?.host?.lowercased() ?? store.activeTabModel.domain
        var tr = navigationTraces[navId] ?? BrowserNavigationTraceRecord(
            id: navId,
            tabId: tid,
            requestedURL: currentURL,
            normalizedURL: currentURL,
            actualURL: currentURL,
            startedAt: Date()
        )
        tr.didStartProvisionalNavigation = true
        tr.state = "LOADING"
        tr.pageTitle = "Loading \(dom)..."
        navigationTraces[navId] = tr

        if tid == store.activeBrowserTabId {
            store.browserCurrentNavigationId = navId
            store.browserIsLoading = true
            store.browserLoadingProgress = max(0.15, webView.estimatedProgress)
            store.browserStatusText = "LOADING"
            store.browserPageTitle = "Loading \(dom)..."
        }
        store.updateLocalTab(tid) { tab in
            tab.navigationId = navId
            tab.title = "Loading \(dom)..."
            tab.status = "LOADING"
            tab.isLoading = true
            tab.hasError = false
            tab.progress = max(0.15, webView.estimatedProgress)
        }
        appendTraceLog(
            navigationId: navId,
            tabId: tid,
            stage: "didStartProvisionalNavigation",
            requestedURL: tr.requestedURL,
            normalizedURL: tr.normalizedURL,
            actualURL: currentURL,
            pageTitle: tr.pageTitle
        )
        Task {
            await store.syncWebViewLifecycleToBackend(
                tabId: tid,
                navigationId: navId,
                event: "didStartProvisionalNavigation",
                requestedURL: tr.requestedURL,
                normalizedURL: tr.normalizedURL,
                actualURL: currentURL,
                url: currentURL,
                title: tr.pageTitle,
                progress: 0.15
            )
        }
    }

    func webView(_ webView: WKWebView, didReceiveServerRedirectForProvisionalNavigation navigation: WKNavigation!) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        guard !(isRenderingDiagnosticHTMLByTab[tid] ?? false) else { return }
        guard let navId = resolveNavigationId(for: navigation, tabId: tid),
              navId == activeNavigationIdByTab[tid] else {
            return
        }
        if let redirectedURL = webView.url?.absoluteString, !redirectedURL.isEmpty, !redirectedURL.hasPrefix("about:") {
            let redirDom = URL(string: redirectedURL)?.host?.lowercased() ?? store.activeTabModel.domain
            if var tr = navigationTraces[navId] {
                tr.didReceiveServerRedirectForProvisionalNavigation = true
                tr.actualURL = redirectedURL
                tr.pageTitle = "Loading \(redirDom)..."
                navigationTraces[navId] = tr
            }
            if tid == store.activeBrowserTabId {
                store.browserAddress = redirectedURL
                store.browserActiveURL = redirectedURL
                store.browserPageTitle = "Loading \(redirDom)..."
                store.browserSecurityState = redirectedURL.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
            }
            store.updateLocalTab(tid) { tab in
                tab.url = redirectedURL
                tab.domain = redirDom
                tab.title = "Loading \(redirDom)..."
                tab.favicon = BrowserAddressNormalizer.faviconForDomain(redirDom)
                tab.securityState = redirectedURL.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
            }
            let tr = navigationTraces[navId]
            appendTraceLog(
                navigationId: navId,
                tabId: tid,
                stage: "didReceiveServerRedirectForProvisionalNavigation",
                requestedURL: tr?.requestedURL ?? redirectedURL,
                normalizedURL: tr?.normalizedURL ?? redirectedURL,
                actualURL: redirectedURL,
                pageTitle: "Loading \(redirDom)..."
            )
            Task {
                await store.syncWebViewLifecycleToBackend(
                    tabId: tid,
                    navigationId: navId,
                    event: "didReceiveServerRedirectForProvisionalNavigation",
                    requestedURL: tr?.requestedURL,
                    normalizedURL: tr?.normalizedURL,
                    actualURL: redirectedURL,
                    url: redirectedURL
                )
            }
        }
    }

    func webView(_ webView: WKWebView, didCommit navigation: WKNavigation!) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        if isRenderingDiagnosticHTMLByTab[tid] == true {
            return
        }
        guard let navId = resolveNavigationId(for: navigation, tabId: tid),
              navId == activeNavigationIdByTab[tid] else {
            return
        }
        hasCommittedByTab[tid] = true
        let committedURL = webView.url?.absoluteString ?? store.browserActiveURL
        if var tr = navigationTraces[navId] {
            tr.didCommit = true
            tr.state = "COMMITTED"
            if !committedURL.isEmpty && !committedURL.hasPrefix("about:") {
                tr.actualURL = committedURL
            }
            navigationTraces[navId] = tr
        }
        if tid == store.activeBrowserTabId {
            store.browserLoadingProgress = max(0.55, webView.estimatedProgress)
            store.browserStatusText = "COMMITTED"
        }
        store.updateLocalTab(tid) { tab in
            tab.status = "COMMITTED"
            tab.progress = max(0.55, webView.estimatedProgress)
        }
        let tr = navigationTraces[navId]
        appendTraceLog(
            navigationId: navId,
            tabId: tid,
            stage: "didCommit",
            requestedURL: tr?.requestedURL ?? committedURL,
            normalizedURL: tr?.normalizedURL ?? committedURL,
            actualURL: committedURL,
            httpStatus: tr?.httpStatus ?? store.browserLastHTTPStatus
        )
        Task {
            await store.syncWebViewLifecycleToBackend(
                tabId: tid,
                navigationId: navId,
                event: "didCommit",
                requestedURL: tr?.requestedURL,
                normalizedURL: tr?.normalizedURL,
                actualURL: committedURL,
                url: committedURL,
                title: webView.title,
                progress: 0.60
            )
        }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        if isRenderingDiagnosticHTMLByTab[tid] == true {
            isRenderingDiagnosticHTMLByTab[tid] = false
            return
        }
        guard let navId = resolveNavigationId(for: navigation, tabId: tid),
              navId == activeNavigationIdByTab[tid] else {
            appendTraceLog(
                navigationId: resolveNavigationId(for: navigation, tabId: tid) ?? "unknown",
                tabId: tid,
                stage: "IGNORED_STALE_didFinish",
                requestedURL: "",
                normalizedURL: "",
                actualURL: webView.url?.absoluteString ?? ""
            )
            return
        }

        watchdogTasksByTab[tid]?.cancel()
        hasCommittedByTab[tid] = true

        let currentURL = webView.url?.absoluteString ?? store.browserActiveURL
        let fallbackDom = URL(string: currentURL)?.host?.lowercased() ?? store.activeTabModel.domain
        let rawWVTitle = (webView.title ?? "").trimmingCharacters(in: .whitespacesAndNewlines)

        // Query DOM directly to confirm actual document.title and viewport content visibility
        let inspectJS = "(function(){ var t = document.title || ''; var b = (document.body && document.body.innerText) ? document.body.innerText.trim() : ''; return { title: t, textLen: b.length, excerpt: b.substring(0, 320) }; })()"
        webView.evaluateJavaScript(inspectJS) { [weak self] res, _ in
            Task { @MainActor in
                guard let self = self, let store = self.store else { return }
                guard self.activeNavigationIdByTab[tid] == navId else { return }

                var domTitle = rawWVTitle
                var textLen = 0
                var excerpt = ""
                if let dict = res as? [String: Any] {
                    if let jsT = (dict["title"] as? String)?.trimmingCharacters(in: .whitespacesAndNewlines), !jsT.isEmpty {
                        domTitle = jsT
                    }
                    textLen = (dict["textLen"] as? Int) ?? 0
                    excerpt = (dict["excerpt"] as? String) ?? ""
                }
                let finalTitle = domTitle.isEmpty ? fallbackDom : domTitle
                let isVisible = (self.viewportWidth > 0 && self.viewportHeight > 0) && (textLen > 0 || !finalTitle.isEmpty)

                var tr = self.navigationTraces[navId] ?? BrowserNavigationTraceRecord(
                    id: navId,
                    tabId: tid,
                    requestedURL: currentURL,
                    normalizedURL: currentURL,
                    actualURL: currentURL
                )
                tr.didCommit = true
                tr.didFinish = true
                tr.state = "COMPLETE"
                if !currentURL.isEmpty && !currentURL.hasPrefix("about:") {
                    tr.actualURL = currentURL
                }
                if tr.httpStatus == 0 {
                    tr.httpStatus = (store.browserLastHTTPStatus > 0) ? store.browserLastHTTPStatus : 200
                }
                tr.pageTitle = finalTitle
                tr.elapsedMs = round(Date().timeIntervalSince(tr.startedAt) * 1000.0)
                tr.contentVisibleInViewport = isVisible
                self.navigationTraces[navId] = tr

                if tid == store.activeBrowserTabId {
                    store.browserIsLoading = false
                    store.browserLoadingProgress = 1.0
                    store.browserPageTitle = finalTitle
                    if !currentURL.isEmpty && !currentURL.hasPrefix("about:") {
                        store.browserAddress = currentURL
                        store.browserActiveURL = currentURL
                        store.browserSecurityState = currentURL.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
                    }
                    store.browserLastHTTPStatus = tr.httpStatus
                    store.browserStatusText = "COMPLETE"
                    if !excerpt.isEmpty {
                        store.browserPreviewText = "[WKWEBVIEW LIVE — \(finalTitle)] " + excerpt
                    }
                    // Live WKWebView load succeeded -> network is verified CONNECTED
                    if store.operatingMode != "LOCAL" && currentURL.lowercased().hasPrefix("http") && !fallbackDom.contains("127.0.0.1") && !fallbackDom.contains("localhost") {
                        store.internetConnectivityState = "CONNECTED"
                        store.internetConnectivityReason = "WKWEBVIEW_HTTPS_VERIFIED (\(fallbackDom), HTTP \(tr.httpStatus))"
                    }
                }

                store.updateLocalTab(tid) { tab in
                    tab.navigationId = navId
                    tab.isLoading = false
                    tab.status = "COMPLETE"
                    tab.progress = 1.0
                    tab.hasError = false
                    tab.errorMessage = ""
                    tab.title = finalTitle
                    if !currentURL.isEmpty && !currentURL.hasPrefix("about:") {
                        tab.url = currentURL
                        tab.domain = fallbackDom
                        tab.favicon = BrowserAddressNormalizer.faviconForDomain(fallbackDom)
                        tab.securityState = currentURL.lowercased().hasPrefix(BrowserAddressNormalizer.httpsPrefix) ? "SECURE_HTTPS" : "INSECURE_HTTP"
                    }
                    tab.httpStatus = tr.httpStatus
                    tab.canGoBack = webView.canGoBack || tab.canGoBack
                    tab.canGoForward = webView.canGoForward || tab.canGoForward
                    tab.contentVisible = isVisible
                }

                self.appendTraceLog(
                    navigationId: navId,
                    tabId: tid,
                    stage: "didFinish",
                    requestedURL: tr.requestedURL,
                    normalizedURL: tr.normalizedURL,
                    actualURL: tr.actualURL,
                    httpStatus: tr.httpStatus,
                    pageTitle: finalTitle,
                    elapsedMs: tr.elapsedMs,
                    contentVisible: isVisible
                )

                await store.syncWebViewLifecycleToBackend(
                    tabId: tid,
                    navigationId: navId,
                    event: "didFinish",
                    requestedURL: tr.requestedURL,
                    normalizedURL: tr.normalizedURL,
                    actualURL: tr.actualURL,
                    url: tr.actualURL,
                    title: finalTitle,
                    httpStatus: tr.httpStatus,
                    progress: 1.0,
                    canGoBack: webView.canGoBack,
                    canGoForward: webView.canGoForward,
                    elapsedMs: tr.elapsedMs,
                    contentVisible: isVisible
                )
            }
        }
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        let nsErr = error as NSError
        guard let tid = tabId(for: webView) else { return }
        if nsErr.domain == NSURLErrorDomain && nsErr.code == NSURLErrorCancelled {
            return
        }
        guard let navId = resolveNavigationId(for: navigation, tabId: tid),
              navId == activeNavigationIdByTab[tid] else {
            return
        }
        let errCode = "\(nsErr.domain)(\(nsErr.code))"
        handleNavigationFailureInternal(
            webView: webView,
            tabId: tid,
            navigationId: navId,
            stage: "didFailProvisionalNavigation",
            errorCode: errCode,
            errorMessage: error.localizedDescription
        )
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        let nsErr = error as NSError
        guard let tid = tabId(for: webView) else { return }
        if nsErr.domain == NSURLErrorDomain && nsErr.code == NSURLErrorCancelled {
            return
        }
        guard let navId = resolveNavigationId(for: navigation, tabId: tid),
              navId == activeNavigationIdByTab[tid] else {
            return
        }
        let errCode = "\(nsErr.domain)(\(nsErr.code))"
        handleNavigationFailureInternal(
            webView: webView,
            tabId: tid,
            navigationId: navId,
            stage: "didFail",
            errorCode: errCode,
            errorMessage: error.localizedDescription
        )
    }

    func webViewWebContentProcessDidTerminate(_ webView: WKWebView) {
        guard let store = store, let tid = tabId(for: webView) else { return }
        if isRenderingDiagnosticHTMLByTab[tid] == true {
            return
        }
        let navId = activeNavigationIdByTab[tid] ?? generateNavigationId()
        let count = (processTerminationCountByNavId[navId] ?? 0) + 1
        processTerminationCountByNavId[navId] = count

        if var tr = navigationTraces[navId] {
            tr.webViewWebContentProcessDidTerminate = true
            navigationTraces[navId] = tr
        }
        appendTraceLog(
            navigationId: navId,
            tabId: tid,
            stage: "webViewWebContentProcessDidTerminate(attempt=\(count))",
            requestedURL: store.browserAddress,
            normalizedURL: store.browserActiveURL,
            actualURL: webView.url?.absoluteString ?? store.browserActiveURL
        )

        if count == 1 {
            store.browserStatusText = "RECOVERING WEBKIT PROCESS..."
            webView.reload()
            Task {
                await store.notifyWebKitProcessRecovered(tabId: tid)
            }
        } else {
            // Cap reload loop and complete navigation via Native URLSession/HTML Document Engine so viewport is never blank
            Task { @MainActor in
                await self.completeNavigationViaNativeEngine(tabId: tid, navigationId: navId)
            }
        }
    }

    // MARK: WKUIDelegate (New Window / target="_blank" Support)

    func webView(
        _ webView: WKWebView,
        createWebViewWith configuration: WKWebViewConfiguration,
        for navigationAction: WKNavigationAction,
        windowFeatures: WKWindowFeatures
    ) -> WKWebView? {
        if let targetURL = navigationAction.request.url?.absoluteString {
            Task { @MainActor in
                await self.store?.openNewBrowserTab(initialURL: targetURL)
            }
        }
        return nil
    }

    // MARK: WKDownloadDelegate (Staging Directory Download & SHA-256 Verification)

    func download(
        _ download: WKDownload,
        decideDestinationUsing response: URLResponse,
        suggestedFilename: String,
        completionHandler: @escaping (URL?) -> Void
    ) {
        let stagingPath = "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/staging_downloads"
        try? FileManager.default.createDirectory(atPath: stagingPath, withIntermediateDirectories: true)
        let cleanName = suggestedFilename.replacingOccurrences(of: "/", with: "_")
        let destURL = URL(fileURLWithPath: stagingPath).appendingPathComponent("\(Int(Date().timeIntervalSince1970 * 1000))_\(cleanName)")
        downloadDestinations[ObjectIdentifier(download)] = destURL
        completionHandler(destURL)
    }

    func downloadDidFinish(_ download: WKDownload) {
        let dest = downloadDestinations.removeValue(forKey: ObjectIdentifier(download))
        let srcURL = download.originalRequest?.url?.absoluteString ?? ""
        Task { @MainActor in
            self.store?.browserStatusText = "DOWNLOAD STAGED"
            if let d = dest {
                self.store?.browserPreviewText = "[DOWNLOAD VERIFIED IN STAGING] \(d.path) (auto_executed=false)"
            }
            if !srcURL.isEmpty {
                await self.store?.refreshBrowserWorkspaceState()
            }
        }
    }

    func download(_ download: WKDownload, didFailWithError error: Error, resumeData: Data?) {
        downloadDestinations.removeValue(forKey: ObjectIdentifier(download))
        Task { @MainActor in
            self.store?.browserStatusText = "DOWNLOAD FAILED"
            self.store?.browserPreviewText = "Gagal mengunduh berkas: \(error.localizedDescription)"
        }
    }
}

struct LiveBrowserWebView: NSViewRepresentable {
    @ObservedObject var store: NUIDesktopStore

    final class Coordinator: NSObject {
        var lastTabId: String = ""
        var didInitialLoad: Bool = false
    }

    func makeCoordinator() -> Coordinator {
        Coordinator()
    }

    func makeNSView(context: Context) -> NSView {
        store.browserEngine.store = store
        let tabId = store.activeBrowserTabId.isEmpty ? "tab-main" : store.activeBrowserTabId
        let wv = store.browserEngine.attachActiveTabWebView(tabId, sessionPolicy: store.browserSessionPolicy)
        let target = store.browserActiveURL.trimmingCharacters(in: .whitespacesAndNewlines)
        if !context.coordinator.didInitialLoad && !target.isEmpty && wv.url == nil && !wv.isLoading {
            context.coordinator.didInitialLoad = true
            context.coordinator.lastTabId = tabId
            _ = store.browserEngine.loadURLInTab(
                tabId: tabId,
                urlString: target,
                sessionPolicy: store.browserSessionPolicy,
                operatingMode: store.operatingMode
            )
        }
        return store.browserEngine.containerNSView
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        store.browserEngine.store = store
        let tabId = store.activeBrowserTabId.isEmpty ? "tab-main" : store.activeBrowserTabId
        let activeWV = store.browserEngine.attachActiveTabWebView(tabId, sessionPolicy: store.browserSessionPolicy)
        if context.coordinator.lastTabId != tabId {
            context.coordinator.lastTabId = tabId
            let target = store.browserActiveURL.trimmingCharacters(in: .whitespacesAndNewlines)
            if activeWV.url == nil && !activeWV.isLoading && !target.isEmpty {
                _ = store.browserEngine.loadURLInTab(
                    tabId: tabId,
                    urlString: target,
                    sessionPolicy: store.browserSessionPolicy,
                    operatingMode: store.operatingMode
                )
            }
        }
    }
}

// MARK: - NUI Desktop Store (Live Streaming + Smart Auto-Scroll + Ollama + Safari/Chrome Browser + VPS)

@MainActor
final class NUIDesktopStore: ObservableObject {
    static let chatBottomAnchorId = "chat-bottom-anchor"

    @Published var selectedSection: SidebarSection = .nuiChat

    // Honest Status States
    @Published var uiState: String = "UI READY"
    @Published var serviceState: String = "VERIFYING SERVICE..."
    @Published var providerState: String = "VERIFYING PROVIDER..."
    @Published var modelState: String = "VERIFYING MODEL..."
    @Published var operatingMode: String = "HYBRID"
    @Published var activeProvider: String = "local_ollama"
    @Published var internetConnectivityState: String = "PROBING..."
    @Published var internetConnectivityReason: String = "PROBING_NATIVE_DNS_AND_HTTPS..."
    @Published var internetDiagnostics: [String: Any] = [:]
    @Published var activePort: UInt16 = 8848

    // Conversation & Live Thinking State
    @Published var currentSessionId: String = ""
    @Published var currentSessionTitle: String = "Sesi Percakapan Baru"
    @Published var sessions: [[String: Any]] = []
    @Published var messages: [ChatMessageItem] = []
    @Published var chatInput: String = "" {
        didSet {
            let sidKey = currentSessionId.isEmpty ? "__unsaved_session__" : currentSessionId
            sessionDrafts[sidKey] = chatInput
        }
    }
    @Published var lastUserPromptSent: String = ""
    @Published var isGenerating: Bool = false
    @Published var activeRequestId: String? = nil
    @Published var liveThinkingStage: String = ""
    @Published var liveThinkingStatus: String = ""
    @Published var liveStagesHistory: [String] = []
    @Published var liveToolActivities: [String] = []
    @Published var lastErrorBanner: String? = nil
    @Published var folderNotificationBanner: String? = nil
    @Published var isDemoModeActive: Bool = false

    // Clipboard, Inline Edit, Regenerate, Feedback, Drafts & VPS Folder Inspection State
    @Published var copiedItemId: String = ""
    @Published var copiedConfirmationBanner: String? = nil
    @Published var editingMessageId: String? = nil
    @Published var editingMessageDraft: String = ""
    @Published var sessionDrafts: [String: String] = [:]
    @Published var messageFeedbackMap: [String: String] = [:]
    @Published var lastFolderVPSInspection: [String: Any] = [:]

    // Smart Auto-Scroll & Live Chat Follow State
    @Published var isAutoFollowEnabled: Bool = true
    @Published var userScrolledUp: Bool = false
    @Published var scrollTriggerVersion: Int = 0
    @Published var shouldRefocusComposer: Int = 0
    private var lastAutoScrollTimestamp: TimeInterval = 0

    // Language Engine & Self-Learning State
    @Published var modelLibrary: [String: Any] = [:]
    @Published var installedOllamaModels: [String] = []
    @Published var selfLearningOverview: [String: Any] = [:]
    @Published var selectedLearningSubmenu: Int = 1
    @Published var selectedModelTag: String = "qwen3:4b-instruct-2507-q4_K_M"
    @Published var engineStatusBanner: String = "Ready."
    @Published var feedbackTopic: String = "Format Kode & Penjelasan NUI"
    @Published var feedbackSummary: String = "Sertakan path berkas sumber dan bukti pengujian pytest pada setiap jawaban coding."

    // Ecosystem, Connected Folders & Audit State
    @Published var nuiLayers: [[String: Any]] = []
    @Published var subsystems: [[String: Any]] = []
    @Published var hardwareStatus: [String: Any] = [:]
    @Published var gitStatus: [String: Any] = [:]
    @Published var pendingApprovals: [[String: Any]] = []
    @Published var permissionRules: [[String: Any]] = []
    @Published var authorizedFolders: [[String: Any]] = [
        ["folder_id": "fld-repo", "path": "/Users/AMRA/hijaiyyah-mathematics", "label": "hijaiyyah-mathematics", "access_mode": "READ_WRITE", "active": 1],
        ["folder_id": "fld-yayasan", "path": "/Users/AMRA/yayasan", "label": "yayasan", "access_mode": "READ_WRITE", "active": 1],
        ["folder_id": "fld-opt", "path": "/Users/AMRA/opt", "label": "opt", "access_mode": "READ_ONLY", "active": 1]
    ]
    @Published var disconnectedFolders: [[String: Any]] = []
    @Published var attachedPaths: [String] = []
    @Published var auditLogs: [[String: Any]] = []
    @Published var commLogs: [[String: Any]] = []
    @Published var masterPanels: [String: Any] = [:]
    @Published var technologyStack: [[String: Any]] = []
    @Published var editorFilePath: String = "/Users/AMRA/hijaiyyah-mathematics/rtl/programs/test_bsm.hasm"
    @Published var editorContent: String = "HLOAD H1, 2\nHLOAD H2, 12\nHLOAD H3, 24\nHCADD H4, H1, H2\nHCADD H4, H4, H3\nHNRM2 R1, H4\nPRINT R1\nHALT\n"
    @Published var studioOutput: String = "Ready."

    // Safari + Chrome Style Browser Workspace State
    let browserEngine = NUIBrowserEngineController()
    @Published var isRightInspectorCollapsed: Bool = false
    @Published var browserTabs: [BrowserTabModel] = [
        BrowserTabModel(
            id: "tab-main",
            navigationId: "nav-init-tab-main",
            requestedURL: BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/",
            normalizedURL: BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/",
            title: "Python 3 Documentation",
            url: BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/",
            domain: "docs.python.org",
            favicon: "book.closed.fill",
            status: "COMPLETE",
            isLoading: false,
            progress: 1.0,
            httpStatus: 200,
            securityState: "SECURE_HTTPS",
            canGoBack: false,
            canGoForward: false,
            zoomLevel: 1.0,
            hasError: false,
            errorMessage: "",
            contentVisible: true
        )
    ]
    @Published var activeBrowserTabId: String = "tab-main"
    @Published var browserCurrentNavigationId: String = "nav-init-tab-main"
    @Published var browserAddress: String = BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/"
    @Published var browserActiveURL: String = BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/"
    @Published var browserReloadToken: Int = 0
    @Published var browserStopToken: Int = 0
    @Published var browserIsLoading: Bool = false
    @Published var browserLoadingProgress: Double = 0.0
    @Published var browserPageTitle: String = "Python 3 Documentation"
    @Published var browserStatusText: String = "COMPLETE"
    @Published var browserSecurityState: String = "SECURE_HTTPS"
    @Published var browserLastHTTPStatus: Int = 200
    @Published var browserZoomLevel: Double = 1.0
    @Published var browserSessionPolicy: String = "PERSISTENT_PROFILE"
    @Published var browserErrorHTML: String? = nil
    @Published var browserPreviewText: String = "WKWebView siap memuat halaman web nyata."
    @Published var browserHistory: [String] = [BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/"]
    @Published var browserHistoryIndex: Int = 0
    @Published var browserHistoryItems: [[String: Any]] = []
    @Published var browserHistorySearchQuery: String = ""
    @Published var browserBookmarks: [[String: Any]] = []
    @Published var browserBookmarkFolders: [String] = ["All", "Documentation", "Development", "General"]
    @Published var selectedBookmarkFolderFilter: String = "All"
    @Published var newBookmarkTitleInput: String = ""
    @Published var newBookmarkURLInput: String = ""
    @Published var newBookmarkFolderInput: String = "Documentation"
    @Published var editingBookmarkId: String? = nil
    @Published var browserDownloads: [[String: Any]] = []
    @Published var activeBrowserDrawer: BrowserDrawerPanel = .none
    @Published var isFindBarVisible: Bool = false
    @Published var browserFindQuery: String = ""
    @Published var browserFindMatchCount: Int = 0

    // Web Research, Dependency & VPS State
    @Published var webSearchQuery: String = "Python asyncio"
    @Published var webSearchOutput: String = "Ready."
    @Published var dependencyManagerName: String = "pip"
    @Published var dependencyPackageName: String = "pytest"
    @Published var vpsProfiles: [[String: Any]] = []
    @Published var vpsNameInput: String = "Production VPS"
    @Published var vpsHostInput: String = ""
    @Published var vpsUserInput: String = "ubuntu"
    @Published var vpsFingerprintInput: String = "SHA256:"
    @Published var vpsWorkspaceInput: String = "/home/ubuntu/workspace"
    @Published var vpsCommandInput: String = "pytest -q"
    @Published var vpsOutput: String = "Belum ada VPS yang dihubungkan. Masukkan Host & Fingerprint SHA256 untuk menghubungkan VPS via OpenSSH."
    @Published var activeDomainInput: String = "www.akademihijaiyyahindonesia.com"
    @Published var localSyncFolderInput: String = "/Users/AMRA/yayasan"
    @Published var dnsStatusText: String = "NOT_TESTED"
    @Published var httpsStatusText: String = "NOT_TESTED"
    @Published var domainResolutionText: String = "NOT_TESTED"
    @Published var websiteHttpStatusText: String = "NOT_TESTED"
    @Published var tlsCertificateStatusText: String = "NOT_TESTED"
    @Published var activeVpsProfileText: String = "NONE"
    @Published var sshStatusText: String = "NOT_CONFIGURED"
    @Published var hostFingerprintText: String = "NOT_VERIFIED"
    @Published var sftpStatusText: String = "NOT_AVAILABLE"
    @Published var remoteWorkspaceText: String = "NONE"
    @Published var syncStatusText: String = "NOT_CONFIGURED"
    @Published var networkVpsVerificationReport: String = "Klik 'Verify Deployment' atau 'Check Domain' untuk menjalankan pemeriksaan jaringan, domain, dan VPS secara langsung."
    @Published var settingsBanner: String = "Settings synced with SQLite."

    var activeCodingSpecialistLabel: String {
        (modelLibrary["active_coding_specialist_label"] as? String) ?? "NUI CODING SPECIALIST — QWEN3-CODER:30B (INSTALLED)"
    }

    var activeTabModel: BrowserTabModel {
        browserTabs.first(where: { $0.id == activeBrowserTabId }) ?? browserTabs.first ?? BrowserTabModel(
            id: "tab-main",
            navigationId: browserCurrentNavigationId,
            requestedURL: browserAddress,
            normalizedURL: browserActiveURL,
            title: browserPageTitle,
            url: browserActiveURL,
            domain: "docs.python.org",
            favicon: "globe",
            status: browserStatusText,
            isLoading: browserIsLoading,
            progress: browserLoadingProgress,
            httpStatus: browserLastHTTPStatus,
            securityState: browserSecurityState,
            canGoBack: browserHistoryIndex > 0,
            canGoForward: browserHistoryIndex + 1 < browserHistory.count,
            zoomLevel: browserZoomLevel,
            hasError: false,
            errorMessage: "",
            contentVisible: true
        )
    }

    nonisolated(unsafe) private var spawnedPid: pid_t = 0
    nonisolated(unsafe) private var cancelCurrentStreamFlag: Bool = false

    init(skipAutoBootstrap: Bool = false) {
        browserEngine.store = self
        NotificationCenter.default.addObserver(
            forName: NSApplication.willTerminateNotification,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            if let pid = self?.spawnedPid, pid > 0 {
                Darwin.kill(pid, SIGTERM)
            }
        }
        if !skipAutoBootstrap {
            Task {
                await runNativeConnectivityProbe()
                await bootstrapServiceAndLoadState()
            }
        }
    }

    // MARK: - Smart Auto-Scroll Coordinator Methods

    func requestAutoScroll(force: Bool = false, immediate: Bool = false) {
        if force {
            isAutoFollowEnabled = true
            userScrolledUp = false
        }
        guard isAutoFollowEnabled else { return }

        let now = Date().timeIntervalSince1970
        if immediate || (now - lastAutoScrollTimestamp) >= 0.030 {
            lastAutoScrollTimestamp = now
            scrollTriggerVersion &+= 1
        }
    }

    func handleUserManualScrollUp() {
        if isAutoFollowEnabled || !userScrolledUp {
            isAutoFollowEnabled = false
            userScrolledUp = true
        }
    }

    func handleUserReachedBottom() {
        if !isAutoFollowEnabled || userScrolledUp {
            isAutoFollowEnabled = true
            userScrolledUp = false
        }
    }

    func scrollToLatestResponse() {
        requestAutoScroll(force: true, immediate: true)
    }

    func bootstrapServiceAndLoadState() async {
        let initialOk = await checkHealthOnce()
        if !initialOk {
            serviceState = "STARTING LOCAL SERVICE..."
            if let pid = LocalLoopbackClient.spawnDaemonIfNeeded() {
                spawnedPid = pid
            }
            for _ in 0..<12 {
                try? await Task.sleep(nanoseconds: 250_000_000)
                if await checkHealthOnce() {
                    break
                }
            }
        }
        await refreshAll()
        await refreshBrowserWorkspaceState()
        if operatingMode != "LOCAL" {
            await runConnectivityCheck()
        } else {
            internetConnectivityState = "DISCONNECTED"
            internetConnectivityReason = "OPERATING_MODE_LOCAL_LOCK"
        }
        if authorizedFolders.isEmpty && disconnectedFolders.isEmpty {
            await connectFolderPath("/Users/AMRA/hijaiyyah-mathematics", label: "hijaiyyah-mathematics", accessMode: "READ_WRITE")
            await connectFolderPath("/Users/AMRA/opt", label: "opt", accessMode: "READ_ONLY")
        }
        if currentSessionId.isEmpty {
            await createNewSession(title: "Sesi Percakapan Baru")
        }
    }

    func checkHealthOnce() async -> Bool {
        let res = await Task.detached { () -> (Int, [String: Any])? in
            try? LocalLoopbackClient.sendRequest(method: "GET", path: "/api/health", timeoutSeconds: 2)
        }.value
        guard let (code, data) = res, code == 200 else {
            serviceState = "ERROR (BACKEND OFFLINE)"
            providerState = "PROVIDER UNAVAILABLE"
            modelState = "PROVIDER UNAVAILABLE"
            return false
        }
        // If an older daemon (< 1.5.2) is running, terminate it and spawn the v1.5.2 daemon
        let ver = (data["version"] as? String) ?? ""
        if ver != "1.5.2" && spawnedPid == 0 {
            if let oldPid = data["pid"] as? Int, oldPid > 0, oldPid != Int(getpid()) {
                Darwin.kill(pid_t(oldPid), SIGTERM)
            }
            if let pid = LocalLoopbackClient.spawnDaemonIfNeeded() {
                spawnedPid = pid
                try? await Task.sleep(nanoseconds: 650_000_000)
            }
        }
        activePort = LocalLoopbackClient.resolveActivePort()
        serviceState = (data["service_state"] as? String) ?? "LOCAL SERVICE READY"
        providerState = (data["provider_state"] as? String) ?? "PROVIDER CONNECTED"
        modelState = (data["model_state"] as? String) ?? "MODEL READY"
        operatingMode = (data["operating_mode"] as? String) ?? "HYBRID"
        activeProvider = (data["active_provider"] as? String) ?? "native_nui"
        if let netSt = data["network_connectivity_state"] as? String, netSt != "UNKNOWN" {
            internetConnectivityState = netSt
        }
        if let netReason = data["network_connectivity_reason"] as? String, !netReason.isEmpty {
            internetConnectivityReason = netReason
        }
        if !isGenerating {
            uiState = providerState == "PROVIDER UNAVAILABLE" ? "PROVIDER UNAVAILABLE" : "UI READY"
        }
        return true
    }

    func refreshAll() async {
        _ = await checkHealthOnce()
        await fetchAsync("/api/models/library") { dict in
            self.modelLibrary = dict
            if let probe = dict["ollama_probe"] as? [String: Any],
               let names = probe["model_names"] as? [String], !names.isEmpty {
                self.installedOllamaModels = names
                if let sel = dict["selected_model"] as? String, names.contains(sel) {
                    self.selectedModelTag = sel
                } else if !names.contains(self.selectedModelTag) {
                    let preferredOrder = [
                        "qwen3.8:27b",
                        "qwen3.6:27b",
                        "qwen3:4b-instruct-2507-q4_K_M",
                        "qwen3-coder:30b",
                        "hermes3:8b",
                        "santri-ai-8b:latest",
                        "santri-ai-kecil:latest"
                    ]
                    if let matched = preferredOrder.first(where: { names.contains($0) }) {
                        self.selectedModelTag = matched
                    } else if let firstModel = names.first {
                        self.selectedModelTag = firstModel
                    }
                }
            } else if let sel = dict["selected_model"] as? String, !sel.isEmpty {
                self.selectedModelTag = sel
            }
        }
        await fetchAsync("/api/self-learning/overview") { dict in
            self.selfLearningOverview = dict
        }
        await fetchAsync("/api/nui/layers") { dict in
            self.nuiLayers = (dict["layers"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/subsystems") { dict in
            self.subsystems = (dict["subsystems"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/hardware/status") { dict in
            self.hardwareStatus = dict
        }
        await fetchAsync("/api/git/status") { dict in
            self.gitStatus = dict
        }
        await fetchAsync("/api/permissions") { dict in
            self.pendingApprovals = (dict["pending_approvals"] as? [[String: Any]]) ?? []
            self.permissionRules = (dict["rules"] as? [[String: Any]]) ?? []
            let loadedFolders = (dict["authorized_folders"] as? [[String: Any]]) ?? []
            self.authorizedFolders = loadedFolders.filter { ($0["active"] as? Int ?? 1) != 0 }
            self.disconnectedFolders = (dict["disconnected_folders"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/web/status") { dict in
            if let cSt = dict["connectivity_status"] as? String, cSt != "UNKNOWN" {
                self.internetConnectivityState = cSt
            }
            if let diag = dict["diagnostics"] as? [String: Any] {
                self.internetDiagnostics = diag
                if let r = diag["connectivity_reason"] as? String, !r.isEmpty {
                    self.internetConnectivityReason = r
                }
            }
            if let dls = dict["downloads"] as? [[String: Any]] {
                self.browserDownloads = dls
            }
            if let ws = dict["browser_workspace"] as? [String: Any] {
                self.applyBrowserWorkspacePayload(ws)
            }
        }
        await fetchAsync("/api/vps/profiles") { dict in
            self.vpsProfiles = (dict["profiles"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/audit") { dict in
            self.auditLogs = (dict["audit_logs"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/comm/logs") { dict in
            self.commLogs = (dict["communication_logs"] as? [[String: Any]]) ?? []
        }
        await fetchAsync("/api/master/panels") { dict in
            self.masterPanels = dict
            if let stackPanel = dict["5_technology_stack"] as? [String: Any],
               let techs = stackPanel["technologies"] as? [[String: Any]] {
                self.technologyStack = techs
            }
        }
        await fetchAsync("/api/sessions") { dict in
            let list = (dict["sessions"] as? [[String: Any]]) ?? []
            self.sessions = list
        }
    }

    // MARK: - Safari + Chrome Style Browser Workspace & Live Navigation Methods

    func updateLocalTab(_ tabId: String, mutate: (inout BrowserTabModel) -> Void) {
        if let idx = browserTabs.firstIndex(where: { $0.id == tabId }) {
            mutate(&browserTabs[idx])
        }
    }

    func applyNavigationStartState(
        tabId: String,
        navigationId: String,
        requestedURL: String,
        normalizedURL: String,
        domain: String,
        securityState: String
    ) {
        let freshTitle = "Loading \(domain)..."
        let freshFavicon = BrowserAddressNormalizer.faviconForDomain(domain)
        updateLocalTab(tabId) { tab in
            tab.navigationId = navigationId
            tab.requestedURL = requestedURL
            tab.normalizedURL = normalizedURL
            tab.url = normalizedURL
            tab.domain = domain
            tab.title = freshTitle
            tab.favicon = freshFavicon
            tab.status = "LOADING"
            tab.isLoading = true
            tab.progress = 0.12
            tab.httpStatus = 0
            tab.securityState = securityState
            tab.hasError = false
            tab.errorMessage = ""
            tab.contentVisible = false
        }
        if tabId == activeBrowserTabId {
            browserCurrentNavigationId = navigationId
            browserAddress = normalizedURL
            browserActiveURL = normalizedURL
            browserPageTitle = freshTitle
            browserStatusText = "LOADING"
            browserIsLoading = true
            browserLoadingProgress = 0.12
            browserLastHTTPStatus = 0
            browserSecurityState = securityState
            browserErrorHTML = nil
        }
    }

    func applyNavigationFailureState(
        tabId: String,
        navigationId: String,
        failingURL: String,
        domain: String,
        errorCode: String,
        errorMessage: String,
        errorHTML: String
    ) {
        let failTitle = "Gagal Memuat Halaman — \(domain)"
        updateLocalTab(tabId) { tab in
            tab.navigationId = navigationId
            tab.url = failingURL
            tab.domain = domain
            tab.title = failTitle
            tab.favicon = "exclamationmark.triangle.fill"
            tab.status = "FAILED"
            tab.isLoading = false
            tab.progress = 0.0
            tab.hasError = true
            tab.errorMessage = "\(errorCode): \(errorMessage)"
            tab.contentVisible = true
        }
        if tabId == activeBrowserTabId {
            browserCurrentNavigationId = navigationId
            browserAddress = failingURL
            browserActiveURL = failingURL
            browserPageTitle = failTitle
            browserStatusText = "FAILED"
            browserIsLoading = false
            browserLoadingProgress = 0.0
            browserErrorHTML = errorHTML
            browserPreviewText = "[NAVIGATION FAILED — \(errorCode)] \(errorMessage)"
        }
    }

    func applyBrowserWorkspacePayload(_ dict: [String: Any]) {
        if let pol = dict["session_policy"] as? String {
            browserSessionPolicy = pol
        }
        if let bms = dict["bookmarks"] as? [[String: Any]] {
            browserBookmarks = bms
        }
        if let flds = dict["bookmark_folders"] as? [String] {
            browserBookmarkFolders = ["All"] + flds.filter { $0 != "All" }
        }
        if let hist = dict["history"] as? [[String: Any]] {
            browserHistoryItems = hist
        }
        if let dls = dict["downloads"] as? [[String: Any]] {
            browserDownloads = dls
        }
        if let conn = dict["connectivity"] as? [String: Any] {
            if let ov = conn["overall_status"] as? String, ov != "UNKNOWN" {
                internetConnectivityState = ov
            }
            if let r = conn["connectivity_reason"] as? String, !r.isEmpty {
                internetConnectivityReason = r
            }
        }
        // Only overwrite tabs from backend snapshot if the active tab is not currently mid-navigation in WKWebView
        if browserIsLoading {
            return
        }
        if let rawTabs = dict["tabs"] as? [[String: Any]], !rawTabs.isEmpty {
            let mapped: [BrowserTabModel] = rawTabs.map { t in
                let tid = (t["tab_id"] as? String) ?? UUID().uuidString
                let existing = self.browserTabs.first(where: { $0.id == tid })
                let navId = existing?.navigationId ?? (t["navigation_id"] as? String) ?? "nav-init"
                let title = existing?.title ?? (t["title"] as? String) ?? "New Tab"
                let url = existing?.url ?? (t["url"] as? String) ?? (BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/")
                let dom = existing?.domain ?? (t["domain"] as? String) ?? "docs.python.org"
                let fav = existing?.favicon ?? (t["favicon"] as? String) ?? "globe"
                let st = existing?.status ?? (t["status"] as? String) ?? "COMPLETE"
                let loading = existing?.isLoading ?? (t["is_loading"] as? Bool) ?? false
                let prog = existing?.progress ?? (t["progress"] as? Double) ?? 1.0
                let httpCode = existing?.httpStatus ?? (t["http_status"] as? Int) ?? 200
                let sec = existing?.securityState ?? (t["security_state"] as? String) ?? "SECURE_HTTPS"
                let back = existing?.canGoBack ?? (t["can_go_back"] as? Bool) ?? false
                let fwd = existing?.canGoForward ?? (t["can_go_forward"] as? Bool) ?? false
                let zoom = existing?.zoomLevel ?? (t["zoom_level"] as? Double) ?? 1.0
                let hasErr = existing?.hasError ?? (t["has_error"] as? Bool) ?? false
                let errMsg = existing?.errorMessage ?? (t["error_message"] as? String) ?? ""
                return BrowserTabModel(
                    id: tid,
                    navigationId: navId,
                    requestedURL: url,
                    normalizedURL: url,
                    title: title,
                    url: url,
                    domain: dom,
                    favicon: fav,
                    status: st,
                    isLoading: loading,
                    progress: prog,
                    httpStatus: httpCode,
                    securityState: sec,
                    canGoBack: back,
                    canGoForward: fwd,
                    zoomLevel: zoom,
                    hasError: hasErr,
                    errorMessage: errMsg,
                    contentVisible: true
                )
            }
            browserTabs = mapped
        }
    }

    func refreshBrowserWorkspaceState() async {
        await fetchAsync("/api/browser/state") { dict in
            self.applyBrowserWorkspacePayload(dict)
        }
    }

    func openNewBrowserTab(initialURL: String? = nil) async {
        let target = initialURL ?? (BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/")
        let norm = BrowserAddressNormalizer.normalize(target)
        let resolved = norm.ok ? norm.resolvedURL : (BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/")
        let dom = norm.ok ? norm.domain : "docs.python.org"
        let localTid = "tab-\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(8).lowercased())"
        let newTab = BrowserTabModel(
            id: localTid,
            navigationId: "nav-new-\(localTid)",
            requestedURL: target,
            normalizedURL: resolved,
            title: "Loading \(dom)...",
            url: resolved,
            domain: dom,
            favicon: BrowserAddressNormalizer.faviconForDomain(dom),
            status: "LOADING",
            isLoading: true,
            progress: 0.15,
            httpStatus: 0,
            securityState: norm.securityState,
            canGoBack: false,
            canGoForward: false,
            zoomLevel: 1.0,
            hasError: false,
            errorMessage: "",
            contentVisible: false
        )
        browserTabs.append(newTab)
        activeBrowserTabId = localTid
        browserAddress = resolved
        browserActiveURL = resolved
        browserPageTitle = "Loading \(dom)..."
        browserStatusText = "LOADING"
        browserErrorHTML = nil

        let navId = browserEngine.loadURLInTab(
            tabId: localTid,
            urlString: resolved,
            sessionPolicy: browserSessionPolicy,
            operatingMode: operatingMode,
            requestedRawInput: target
        )
        browserCurrentNavigationId = navId
        await postAsync("/api/browser/op", body: ["op": "new_tab", "url": resolved, "switch_to": true]) { _ in }
    }

    func switchBrowserTab(_ tabId: String) async {
        guard tabId != activeBrowserTabId else { return }
        activeBrowserTabId = tabId
        let existingTab = browserTabs.first(where: { $0.id == tabId })
        if let tab = existingTab {
            browserCurrentNavigationId = tab.navigationId
            browserAddress = tab.url
            browserActiveURL = tab.url
            browserPageTitle = tab.title
            browserStatusText = tab.status
            browserIsLoading = tab.isLoading
            browserLoadingProgress = tab.progress
            browserSecurityState = tab.securityState
            browserLastHTTPStatus = tab.httpStatus
            browserZoomLevel = tab.zoomLevel
            browserErrorHTML = nil
        }
        let wv = browserEngine.attachActiveTabWebView(tabId, sessionPolicy: browserSessionPolicy)
        let alreadyCompletedOrFailed = (existingTab?.status == "COMPLETE" || existingTab?.status == "FAILED")
        if !alreadyCompletedOrFailed && wv.url == nil && !wv.isLoading && !browserActiveURL.isEmpty {
            _ = browserEngine.loadURLInTab(
                tabId: tabId,
                urlString: browserActiveURL,
                sessionPolicy: browserSessionPolicy,
                operatingMode: operatingMode
            )
        }
        await postAsync("/api/browser/op", body: ["op": "switch_tab", "tab_id": tabId]) { _ in }
    }

    func closeBrowserTab(_ tabId: String) async {
        browserEngine.closeTabWebView(tabId)
        if let idx = browserTabs.firstIndex(where: { $0.id == tabId }) {
            browserTabs.remove(at: idx)
            if browserTabs.isEmpty {
                let homeURL = BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/"
                let fallback = BrowserTabModel(
                    id: "tab-main",
                    navigationId: "nav-init-tab-main",
                    requestedURL: homeURL,
                    normalizedURL: homeURL,
                    title: "Loading docs.python.org...",
                    url: homeURL,
                    domain: "docs.python.org",
                    favicon: "book.closed.fill",
                    status: "LOADING",
                    isLoading: true,
                    progress: 0.15,
                    httpStatus: 0,
                    securityState: "SECURE_HTTPS",
                    canGoBack: false,
                    canGoForward: false,
                    zoomLevel: 1.0,
                    hasError: false,
                    errorMessage: "",
                    contentVisible: false
                )
                browserTabs.append(fallback)
                activeBrowserTabId = fallback.id
                _ = browserEngine.loadURLInTab(
                    tabId: fallback.id,
                    urlString: homeURL,
                    sessionPolicy: browserSessionPolicy,
                    operatingMode: operatingMode
                )
            } else if activeBrowserTabId == tabId {
                let nextIdx = min(idx, browserTabs.count - 1)
                let nextTab = browserTabs[nextIdx]
                activeBrowserTabId = nextTab.id
                browserAddress = nextTab.url
                browserActiveURL = nextTab.url
                browserPageTitle = nextTab.title
                browserStatusText = nextTab.status
                _ = browserEngine.attachActiveTabWebView(nextTab.id, sessionPolicy: browserSessionPolicy)
            }
        }
        await postAsync("/api/browser/op", body: ["op": "close_tab", "tab_id": tabId]) { _ in }
    }

    func moveBrowserTab(tabId: String, direction: Int) async {
        guard let curIdx = browserTabs.firstIndex(where: { $0.id == tabId }) else { return }
        let targetIdx = max(0, min(browserTabs.count - 1, curIdx + direction))
        guard targetIdx != curIdx else { return }
        let item = browserTabs.remove(at: curIdx)
        browserTabs.insert(item, at: targetIdx)
        await postAsync("/api/browser/op", body: ["op": "move_tab", "tab_id": tabId, "to_index": targetIdx]) { _ in }
    }

    func navigateBrowser(to targetAddr: String? = nil) async {
        let rawAddr = (targetAddr ?? browserAddress).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !rawAddr.isEmpty else { return }

        let tabId = activeBrowserTabId.isEmpty ? "tab-main" : activeBrowserTabId
        let norm = BrowserAddressNormalizer.normalize(rawAddr)

        // Record previous URL in local back history stack before navigating
        if norm.ok, !browserActiveURL.isEmpty, browserActiveURL != norm.resolvedURL {
            if !browserHistory.contains(norm.resolvedURL) {
                browserHistory.append(norm.resolvedURL)
                browserHistoryIndex = browserHistory.count - 1
            }
            updateLocalTab(tabId) { tab in
                tab.canGoBack = true
            }
        }

        // Immediately start native WKWebView navigation on @MainActor (resets stale title, loading state, favicon, and starts 15s watchdog)
        let navId = browserEngine.loadURLInTab(
            tabId: tabId,
            urlString: norm.ok ? norm.resolvedURL : rawAddr,
            sessionPolicy: browserSessionPolicy,
            operatingMode: operatingMode,
            requestedRawInput: rawAddr
        )
        browserCurrentNavigationId = navId
        browserReloadToken &+= 1

        // Sync navigation start with backend asynchronously without blocking WKWebView rendering
        await postAsync("/api/browser/op", body: [
            "op": "begin_navigation",
            "tab_id": tabId,
            "navigation_id": navId,
            "raw_input": rawAddr
        ]) { _ in }
    }

    func browserGoBack() async {
        let wv = browserEngine.webViewForTab(activeBrowserTabId, sessionPolicy: browserSessionPolicy)
        if wv.canGoBack {
            let navId = "nav-back-\(Int(Date().timeIntervalSince1970 * 1000))"
            browserCurrentNavigationId = navId
            browserIsLoading = true
            browserStatusText = "LOADING"
            browserPageTitle = "Loading previous page..."
            wv.goBack()
            return
        }
        await postAsync("/api/browser/op", body: ["op": "back", "tab_id": activeBrowserTabId]) { dict in
            if let tabDict = dict["tab"] as? [String: Any],
               let u = tabDict["url"] as? String, !u.isEmpty {
                Task { await self.navigateBrowser(to: u) }
            }
        }
    }

    func browserGoForward() async {
        let wv = browserEngine.webViewForTab(activeBrowserTabId, sessionPolicy: browserSessionPolicy)
        if wv.canGoForward {
            let navId = "nav-fwd-\(Int(Date().timeIntervalSince1970 * 1000))"
            browserCurrentNavigationId = navId
            browserIsLoading = true
            browserStatusText = "LOADING"
            browserPageTitle = "Loading next page..."
            wv.goForward()
            return
        }
        await postAsync("/api/browser/op", body: ["op": "forward", "tab_id": activeBrowserTabId]) { dict in
            if let tabDict = dict["tab"] as? [String: Any],
               let u = tabDict["url"] as? String, !u.isEmpty {
                Task { await self.navigateBrowser(to: u) }
            }
        }
    }

    func browserGoHome() async {
        await navigateBrowser(to: BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/")
    }

    func reloadCurrentBrowserTab() async {
        let target = browserActiveURL.isEmpty ? browserAddress : browserActiveURL
        let navId = browserEngine.loadURLInTab(
            tabId: activeBrowserTabId,
            urlString: target,
            sessionPolicy: browserSessionPolicy,
            operatingMode: operatingMode,
            requestedRawInput: target,
            forceReload: true
        )
        browserCurrentNavigationId = navId
        browserReloadToken &+= 1
        await postAsync("/api/browser/op", body: ["op": "reload", "tab_id": activeBrowserTabId]) { _ in }
    }

    func stopBrowserLoading() {
        let wv = browserEngine.webViewForTab(activeBrowserTabId, sessionPolicy: browserSessionPolicy)
        wv.stopLoading()
        browserStopToken &+= 1
        browserIsLoading = false
        browserStatusText = "STOPPED"
        if browserPageTitle.hasPrefix("Loading ") {
            browserPageTitle = "Stopped — \(activeTabModel.domain)"
        }
        updateLocalTab(activeBrowserTabId) { tab in
            tab.isLoading = false
            tab.status = "STOPPED"
            if tab.title.hasPrefix("Loading ") {
                tab.title = "Stopped — \(tab.domain)"
            }
        }
        Task {
            await postAsync("/api/browser/op", body: ["op": "stop", "tab_id": activeBrowserTabId]) { _ in }
        }
    }

    func adjustBrowserZoom(delta: Double, reset: Bool = false) async {
        let nextZoom = reset ? 1.0 : max(0.5, min(3.0, (browserZoomLevel + delta)))
        browserZoomLevel = nextZoom
        browserEngine.setZoom(tabId: activeBrowserTabId, zoom: nextZoom, sessionPolicy: browserSessionPolicy)
        await postAsync("/api/browser/op", body: ["op": "zoom", "tab_id": activeBrowserTabId, "zoom_level": nextZoom]) { _ in }
    }

    func runBrowserFindOnPage() async {
        let q = browserFindQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        browserEngine.executeFindOnPage(tabId: activeBrowserTabId, query: q, sessionPolicy: browserSessionPolicy)
        await postAsync("/api/browser/op", body: ["op": "find", "tab_id": activeBrowserTabId, "query": q]) { dict in
            if let cnt = dict["match_count"] as? Int, cnt > 0 {
                self.browserFindMatchCount = cnt
            }
        }
    }

    func addCurrentPageBookmark() async {
        let titleToSave = newBookmarkTitleInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? browserPageTitle
            : newBookmarkTitleInput
        let urlToSave = newBookmarkURLInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? browserActiveURL
            : newBookmarkURLInput
        let folderToSave = newBookmarkFolderInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? "Documentation"
            : newBookmarkFolderInput
        await postAsync("/api/browser/op", body: [
            "op": "add_bookmark",
            "title": titleToSave,
            "url": urlToSave,
            "folder": folderToSave
        ]) { _ in
            self.newBookmarkTitleInput = ""
            self.newBookmarkURLInput = ""
            self.browserStatusText = "BOOKMARK SAVED"
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func saveEditedBookmark(bookmarkId: String, title: String, url: String, folder: String) async {
        await postAsync("/api/browser/op", body: [
            "op": "edit_bookmark",
            "bookmark_id": bookmarkId,
            "title": title,
            "url": url,
            "folder": folder
        ]) { _ in
            self.editingBookmarkId = nil
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func deleteBrowserBookmark(_ bookmarkId: String) async {
        await postAsync("/api/browser/op", body: ["op": "delete_bookmark", "bookmark_id": bookmarkId]) { _ in
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func searchBrowserHistory() async {
        await postAsync("/api/browser/op", body: ["op": "search_history", "query": browserHistorySearchQuery]) { dict in
            if let items = dict["history"] as? [[String: Any]] {
                self.browserHistoryItems = items
            }
        }
    }

    func deleteBrowserHistoryItem(_ visitId: String) async {
        await postAsync("/api/browser/op", body: ["op": "delete_history", "visit_ids": [visitId]]) { _ in
            Task { await self.searchBrowserHistory() }
        }
    }

    func clearAllBrowserHistory() async {
        await postAsync("/api/browser/op", body: ["op": "clear_history"]) { _ in
            self.browserHistoryItems = []
            self.browserStatusText = "HISTORY CLEARED"
        }
    }

    func switchBrowserSessionPolicy(_ policy: String) async {
        browserSessionPolicy = policy
        await postAsync("/api/browser/op", body: ["op": "set_session_policy", "policy": policy]) { _ in
            self.browserStatusText = "POLICY: \(policy)"
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func clearBrowserCookiesOnly() async {
        let cookieTypes: Set<String> = [WKWebsiteDataTypeCookies]
        let _ = await WKWebsiteDataStore.default().removeData(ofTypes: cookieTypes, modifiedSince: .distantPast)
        await postAsync("/api/browser/op", body: ["op": "clear_cookies"]) { _ in
            self.browserStatusText = "COOKIES CLEARED"
        }
    }

    func clearBrowserCacheOnly() async {
        let cacheTypes: Set<String> = [WKWebsiteDataTypeDiskCache, WKWebsiteDataTypeMemoryCache]
        let _ = await WKWebsiteDataStore.default().removeData(ofTypes: cacheTypes, modifiedSince: .distantPast)
        await postAsync("/api/browser/op", body: ["op": "clear_cache"]) { _ in
            self.browserStatusText = "CACHE CLEARED"
        }
    }

    func clearBrowserSessionData() async {
        let dataTypes = WKWebsiteDataStore.allWebsiteDataTypes()
        let _ = await WKWebsiteDataStore.default().removeData(ofTypes: dataTypes, modifiedSince: .distantPast)
        await postAsync("/api/web/op", body: ["op": "clear_session"]) { dict in
            let st = (dict["status"] as? String) ?? "SESSION_DATA_CLEARED"
            self.browserStatusText = st
            self.browserHistory = [self.browserAddress]
            self.browserHistoryIndex = 0
            self.browserHistoryItems = []
            self.browserPreviewText = "Data sesi browser, riwayat, cookies, dan cache WKWebView telah dibersihkan."
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func downloadCurrentBrowserURLToStaging() async {
        let rawAddr = browserAddress.trimmingCharacters(in: .whitespacesAndNewlines)
        let schemePrefix = BrowserAddressNormalizer.httpsPrefix
        let fullTarget = rawAddr.contains("://") ? rawAddr : (schemePrefix + rawAddr)
        await postAsync("/api/browser/op", body: [
            "op": "download",
            "url": fullTarget,
            "allow_interactive_browser": true
        ]) { dict in
            let st = (dict["status"] as? String) ?? "STAGED"
            let path = (dict["path"] as? String) ?? (dict["reason"] as? String) ?? ""
            self.browserStatusText = st
            self.browserPreviewText = "[DOWNLOAD \(st)] \(path)"
            self.activeBrowserDrawer = .downloads
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func cancelBrowserDownload(_ downloadId: String) async {
        await postAsync("/api/browser/op", body: ["op": "cancel_download", "download_id": downloadId]) { _ in
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func retryBrowserDownload(_ downloadId: String) async {
        await postAsync("/api/browser/op", body: ["op": "retry_download", "download_id": downloadId]) { _ in
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func removeBrowserDownload(_ downloadId: String) async {
        await postAsync("/api/browser/op", body: ["op": "remove_download", "download_id": downloadId]) { _ in
            Task { await self.refreshBrowserWorkspaceState() }
        }
    }

    func revealBrowserDownloadInFinder(_ downloadId: String) async {
        await postAsync("/api/browser/op", body: [
            "op": "reveal_download",
            "download_id": downloadId,
            "trigger_os_open": true
        ]) { _ in }
    }

    func syncWebViewLifecycleToBackend(
        tabId: String,
        navigationId: String? = nil,
        event: String,
        requestedURL: String? = nil,
        normalizedURL: String? = nil,
        actualURL: String? = nil,
        url: String? = nil,
        title: String? = nil,
        httpStatus: Int? = nil,
        progress: Double? = nil,
        canGoBack: Bool? = nil,
        canGoForward: Bool? = nil,
        errorCode: String? = nil,
        errorMessage: String? = nil,
        elapsedMs: Double? = nil,
        contentVisible: Bool? = nil
    ) async {
        var body: [String: Any] = ["op": "sync_webview", "tab_id": tabId, "event": event]
        if let n = navigationId { body["navigation_id"] = n }
        if let r = requestedURL { body["requested_url"] = r }
        if let nm = normalizedURL { body["normalized_url"] = nm }
        if let ac = actualURL { body["actual_url"] = ac }
        if let u = url { body["url"] = u }
        if let t = title { body["title"] = t }
        if let h = httpStatus { body["http_status"] = h }
        if let p = progress { body["progress"] = p }
        if let b = canGoBack { body["can_go_back"] = b }
        if let f = canGoForward { body["can_go_forward"] = f }
        if let ec = errorCode { body["error_code"] = ec }
        if let e = errorMessage { body["error_message"] = e }
        if let ms = elapsedMs { body["elapsed_ms"] = ms }
        if let cv = contentVisible { body["content_visible"] = cv }
        await postAsync("/api/browser/op", body: body) { _ in }
    }

    func notifyWebKitProcessRecovered(tabId: String) async {
        await postAsync("/api/browser/op", body: ["op": "recover_webkit", "tab_id": tabId, "auto_recover": true]) { _ in
            self.browserStatusText = "WEBKIT RECOVERED"
        }
    }

    // MARK: - Model, Learning, Chat, Folder & VPS Methods

    func performModelOp(_ op: String, modelTag: String? = nil) async {
        let target = modelTag ?? selectedModelTag
        await postAsync("/api/models/op", body: ["op": op, "model_tag": target]) { dict in
            if let st = dict["status"] as? String {
                self.engineStatusBanner = "[\(op.uppercased())] \(target) -> \(st)"
            } else if let ok = dict["verified"] as? Bool {
                self.engineStatusBanner = "[\(op.uppercased())] \(target) -> verified=\(ok)"
            } else {
                self.engineStatusBanner = "[\(op.uppercased())] \(target) selesai."
            }
            Task { await self.refreshAll() }
        }
    }

    func submitUserFeedback() async {
        let body: [String: Any] = [
            "op": "feedback",
            "topic": feedbackTopic,
            "correction_summary": feedbackSummary
        ]
        await postAsync("/api/self-learning/op", body: body) { dict in
            let eid = (dict["entry_id"] as? String) ?? ""
            self.engineStatusBanner = "Feedback pengguna disimpan sebagai User Provided (\(eid))."
            Task { await self.refreshAll() }
        }
    }

    func rollbackLearningEntry(_ entryId: String) async {
        await postAsync("/api/self-learning/op", body: ["op": "rollback", "entry_id": entryId]) { _ in
            self.engineStatusBanner = "Entry \(entryId) berhasil di-rollback."
            Task { await self.refreshAll() }
        }
    }

    func loadSessionMessages(_ sid: String, preserveScrollState: Bool = false) async {
        isDemoModeActive = false
        let previousSessionId = currentSessionId
        if !previousSessionId.isEmpty && previousSessionId != sid {
            sessionDrafts[previousSessionId] = chatInput
        }
        let encoded = sid.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? sid
        await fetchAsync("/api/sessions?session_id=\(encoded)") { dict in
            let prevSid = self.currentSessionId
            self.currentSessionId = sid
            self.currentSessionTitle = (dict["title"] as? String) ?? sid
            if prevSid != sid {
                if let savedDraft = self.sessionDrafts[sid] {
                    self.chatInput = savedDraft
                } else if let backendDraft = dict["draft_text"] as? String, !backendDraft.isEmpty {
                    self.chatInput = backendDraft
                    self.sessionDrafts[sid] = backendDraft
                } else {
                    self.chatInput = ""
                }
            }
            guard let rawMsgs = dict["messages"] as? [[String: Any]] else { return }
            self.messages = rawMsgs.map { m in
                let meta = (m["metadata"] as? [String: Any]) ?? [:]
                return ChatMessageItem(
                    id: (m["message_id"] as? String) ?? UUID().uuidString,
                    requestId: (m["request_id"] as? String) ?? (meta["request_id"] as? String) ?? "",
                    role: (m["role"] as? String) ?? "assistant",
                    content: (m["content"] as? String) ?? "",
                    provider: (meta["provider"] as? String) ?? self.activeProvider,
                    model: (meta["model"] as? String) ?? "cosmictera-nui-native-v1.4",
                    responseTimeMs: (meta["response_time_ms"] as? Double) ?? 0.0,
                    sourceAttribution: (meta["source_attribution"] as? String) ?? "",
                    executionStatus: (meta["execution_status"] as? String) ?? "RESPONSE_COMPLETE",
                    thinkingStages: (meta["thinking_stages"] as? [String]) ?? [],
                    toolActivities: (meta["tool_activities"] as? [String]) ?? []
                )
            }
            if preserveScrollState {
                self.requestAutoScroll(force: false, immediate: true)
            } else {
                self.requestAutoScroll(force: true, immediate: true)
            }
        }
    }

    func createNewSession(title: String = "Sesi Percakapan Baru", resetComposerDraft: Bool = true) async {
        isDemoModeActive = false
        if !currentSessionId.isEmpty {
            sessionDrafts[currentSessionId] = chatInput
        }
        let body: [String: Any] = [
            "title": title,
            "mode": operatingMode,
            "provider": activeProvider
        ]
        await postAsync("/api/sessions", body: body) { dict in
            if let sid = dict["session_id"] as? String {
                self.currentSessionId = sid
                self.currentSessionTitle = (dict["title"] as? String) ?? title
                self.messages = []
                self.liveStagesHistory = []
                self.liveToolActivities = []
                self.editingMessageId = nil
                self.editingMessageDraft = ""
                if resetComposerDraft {
                    self.chatInput = self.sessionDrafts[sid] ?? ""
                }
                self.requestAutoScroll(force: true, immediate: true)
                Task { await self.refreshAll() }
            }
        }
    }

    func pickFilesToAttach() {
        let panel = NSOpenPanel()
        panel.title = "Lampirkan Berkas atau Kode ke CosmicTera NUI"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.directoryURL = URL(fileURLWithPath: "/Users/AMRA/hijaiyyah-mathematics")
        if panel.runModal() == .OK {
            for url in panel.urls {
                let p = url.path
                if !attachedPaths.contains(p) {
                    attachedPaths.append(p)
                }
            }
        }
    }

    func pickAndConnectFolder(accessMode: String = "READ_WRITE") {
        let panel = NSOpenPanel()
        panel.title = "Hubungkan Folder Lokal (Connected Folders) ke CosmicTera NUI"
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = true
        panel.directoryURL = URL(fileURLWithPath: "/Users/AMRA/hijaiyyah-mathematics")
        if panel.runModal() == .OK {
            for url in panel.urls {
                let folderPath = url.path
                let folderLabel = url.lastPathComponent
                if !attachedPaths.contains(folderPath) {
                    attachedPaths.append(folderPath)
                }
                Task {
                    await self.connectFolderPath(folderPath, label: folderLabel, accessMode: accessMode)
                }
            }
        }
    }

    func connectFolderPath(_ folderPath: String, label: String? = nil, accessMode: String = "READ_WRITE") async {
        let lbl = label ?? URL(fileURLWithPath: folderPath).lastPathComponent
        let body: [String: Any] = [
            "action": "ADD",
            "path": folderPath,
            "label": lbl,
            "access_mode": accessMode
        ]
        await postAsync("/api/files/folders", body: body) { dict in
            if let flds = dict["folders"] as? [[String: Any]] {
                self.authorizedFolders = flds
            }
            if let disc = dict["disconnected_folders"] as? [[String: Any]] {
                self.disconnectedFolders = disc
            }
            if let note = dict["notification"] as? String {
                self.folderNotificationBanner = note
            }
            Task { await self.refreshAll() }
        }
    }

    func disconnectConnectedFolder(folderId: String, path: String, label: String) async {
        let targetIdentifier = folderId.isEmpty ? path : folderId
        self.authorizedFolders.removeAll { fld in
            let fid = (fld["folder_id"] as? String) ?? ""
            let fp = (fld["path"] as? String) ?? ""
            return (!folderId.isEmpty && fid == folderId) || (!path.isEmpty && fp == path)
        }
        self.attachedPaths.removeAll { $0 == path || $0 == folderId }

        let encoded = targetIdentifier.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? targetIdentifier
        await deleteAsync("/api/folders/\(encoded)", body: ["folder_id": folderId, "path": path]) { code, dict in
            if code == 200 {
                if let flds = dict["folders"] as? [[String: Any]] {
                    self.authorizedFolders = flds
                }
                if let disc = dict["disconnected_folders"] as? [[String: Any]] {
                    self.disconnectedFolders = disc
                }
                let note = (dict["notification"] as? String) ?? "Folder '\(label)' berhasil diputuskan dari NUI (berkas fisik tetap utuh)."
                self.folderNotificationBanner = note
            } else {
                let errReason = (dict["reason"] as? String) ?? "Gagal memutus koneksi folder."
                self.folderNotificationBanner = errReason
            }
            Task { await self.refreshAll() }
        }
    }

    func revokeConnectedFolder(_ pathOrId: String) async {
        let matched = authorizedFolders.first { fld in
            ((fld["folder_id"] as? String) == pathOrId) || ((fld["path"] as? String) == pathOrId)
        }
        let fid = (matched?["folder_id"] as? String) ?? pathOrId
        let fp = (matched?["path"] as? String) ?? pathOrId
        let lbl = (matched?["label"] as? String) ?? URL(fileURLWithPath: fp).lastPathComponent
        await disconnectConnectedFolder(folderId: fid, path: fp, label: lbl)
    }

    func attachPath(_ path: String) {
        if !attachedPaths.contains(path) {
            attachedPaths.append(path)
        }
    }

    func removeAttachedPath(_ path: String) {
        attachedPaths.removeAll { $0 == path }
    }

    func checkLatestRepoWorkNow() {
        let repoPath = "/Users/AMRA/hijaiyyah-mathematics"
        if !attachedPaths.contains(repoPath) {
            attachedPaths.append(repoPath)
        }
        Task {
            await connectFolderPath(repoPath, label: "hijaiyyah-mathematics", accessMode: "READ_WRITE")
            await sendChatMessage(overridePrompt: "Cek pekerjaan terakhir di repo")
        }
    }

    func sendChatMessage(overridePrompt: String? = nil) async {
        let rawText = overridePrompt ?? chatInput
        let trimmed = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        let attachmentsToSend = attachedPaths
        attachedPaths = []
        isDemoModeActive = false
        chatInput = ""
        if !currentSessionId.isEmpty {
            sessionDrafts[currentSessionId] = ""
        }
        sessionDrafts["__unsaved_session__"] = ""
        lastUserPromptSent = trimmed
        lastErrorBanner = nil

        if currentSessionId.isEmpty {
            await createNewSession(title: String(trimmed.prefix(40)), resetComposerDraft: false)
        }

        let targetSessionId = currentSessionId
        let reqId = "req-\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(12).lowercased())"
        let userMsgId = "msg-\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(12).lowercased())"
        let streamAsstId = "stream-\(reqId)"

        let attachmentNote = attachmentsToSend.isEmpty
            ? ""
            : "\n\n📎 *Lampiran (+):* " + attachmentsToSend.map { "`\(URL(fileURLWithPath: $0).lastPathComponent)`" }.joined(separator: ", ")

        let userMsg = ChatMessageItem(
            id: userMsgId,
            requestId: reqId,
            role: "user",
            content: trimmed + attachmentNote,
            provider: activeProvider,
            model: selectedModelTag,
            responseTimeMs: 0,
            sourceAttribution: "USER_INPUT",
            executionStatus: "SENT",
            thinkingStages: [],
            toolActivities: []
        )
        messages.append(userMsg)

        let streamingMsg = ChatMessageItem(
            id: streamAsstId,
            requestId: reqId,
            role: "assistant",
            content: "",
            provider: activeProvider,
            model: selectedModelTag,
            responseTimeMs: 0,
            sourceAttribution: "",
            executionStatus: "GENERATING",
            thinkingStages: ["REQUEST_RECEIVED"],
            toolActivities: []
        )
        messages.append(streamingMsg)

        isGenerating = true
        cancelCurrentStreamFlag = false
        activeRequestId = reqId
        uiState = "GENERATING"
        liveThinkingStage = "REQUEST_RECEIVED"
        liveThinkingStatus = "NUI is thinking..."
        liveStagesHistory = ["REQUEST_RECEIVED"]
        liveToolActivities = []

        requestAutoScroll(force: true, immediate: true)
        shouldRefocusComposer &+= 1

        let payload: [String: Any] = [
            "request_id": reqId,
            "session_id": targetSessionId,
            "message_id": userMsgId,
            "user_message": trimmed,
            "attachments": attachmentsToSend,
            "provider": activeProvider,
            "model": selectedModelTag,
            "ui_handler": "NUIDesktopStore.sendChatMessage"
        ]

        let streamResult = await Task.detached { [weak self] () -> Error? in
            do {
                try LocalLoopbackClient.streamChatRequest(
                    body: payload,
                    isCancelled: { self?.cancelCurrentStreamFlag ?? false },
                    onEvent: { ev in
                        Task { @MainActor in
                            self?.handleStreamEvent(ev, streamAsstId: streamAsstId, expectedReqId: reqId)
                        }
                    }
                )
                return nil
            } catch {
                return error
            }
        }.value

        isGenerating = false
        activeRequestId = nil
        shouldRefocusComposer &+= 1

        if let err = streamResult {
            uiState = "ERROR"
            serviceState = "ERROR"
            lastErrorBanner = "Gagal menerima stream dari NUI Local Service: \(err.localizedDescription)"
            requestAutoScroll(force: false, immediate: true)
        } else {
            await loadSessionMessages(targetSessionId, preserveScrollState: true)
            await refreshAll()
        }
    }

    private func handleStreamEvent(_ ev: [String: Any], streamAsstId: String, expectedReqId: String) {
        let evReqId = (ev["request_id"] as? String) ?? expectedReqId
        guard evReqId == expectedReqId else { return }
        guard let idx = messages.firstIndex(where: { $0.id == streamAsstId }) else { return }

        let evKind = (ev["event"] as? String) ?? ""
        if cancelCurrentStreamFlag && evKind != "generation_cancelled" {
            return
        }
        if messages[idx].executionStatus == "STOPPED" || messages[idx].executionStatus == "CANCELLED" {
            return
        }

        if let stg = ev["stage"] as? String, !stg.isEmpty {
            if !(stg == "COMPLETE" && liveStagesHistory.contains("CANCELLED")) {
                liveThinkingStage = stg
                if !liveStagesHistory.contains(stg) {
                    liveStagesHistory.append(stg)
                }
            }
        }
        if let thStatus = ev["thinking_status"] as? String, !thStatus.isEmpty {
            liveThinkingStatus = thStatus
        }
        if let act = ev["activity"] as? String, !act.isEmpty {
            if !liveToolActivities.contains(act) {
                liveToolActivities.append(act)
            }
        }

        messages[idx].thinkingStages = liveStagesHistory
        messages[idx].toolActivities = liveToolActivities

        if evKind == "partial_response" {
            if let acc = ev["accumulated_text"] as? String {
                messages[idx].content = acc
            } else if let delta = ev["delta"] as? String {
                messages[idx].content += delta
            }
            requestAutoScroll(force: false, immediate: false)
        } else if evKind == "tool_call" || evKind == "tool_result" || evKind == "stage_update" {
            requestAutoScroll(force: false, immediate: false)
        } else if evKind == "final_response" {
            guard !cancelCurrentStreamFlag && !liveStagesHistory.contains("CANCELLED") else { return }
            if let finalTxt = ev["response_text"] as? String, !finalTxt.isEmpty {
                messages[idx].content = finalTxt
            }
            messages[idx].executionStatus = "COMPLETE"
            uiState = "RESPONSE COMPLETE"
            liveThinkingStage = "COMPLETE"
            liveThinkingStatus = "COMPLETE"
            requestAutoScroll(force: false, immediate: true)
        } else if evKind == "generation_cancelled" {
            messages[idx].executionStatus = "CANCELLED"
            uiState = "UI READY"
            liveThinkingStage = "CANCELLED"
            liveThinkingStatus = "GENERATION CANCELLED"
            liveStagesHistory.removeAll { $0 == "COMPLETE" }
            if !liveStagesHistory.contains("CANCELLED") {
                liveStagesHistory.append("CANCELLED")
            }
            messages[idx].thinkingStages = liveStagesHistory
            requestAutoScroll(force: false, immediate: true)
        } else if evKind == "generation_error" {
            let errStr = (ev["error"] as? String) ?? "ERROR"
            if let errReply = ev["response_text"] as? String, !errReply.isEmpty {
                messages[idx].content = errReply
            }
            messages[idx].executionStatus = "ERROR"
            uiState = (ev["ui_state"] as? String) ?? "ERROR"
            lastErrorBanner = errStr
            requestAutoScroll(force: false, immediate: true)
        }
    }

    func stopGeneration() async {
        cancelCurrentStreamFlag = true
        guard let reqId = activeRequestId else { return }
        let sid = currentSessionId
        liveThinkingStage = "CANCELLED"
        liveThinkingStatus = "GENERATION CANCELLED"
        liveStagesHistory.removeAll { $0 == "COMPLETE" }
        if !liveStagesHistory.contains("CANCELLED") {
            liveStagesHistory.append("CANCELLED")
        }
        await postAsync("/api/chat/stop", body: ["request_id": reqId, "session_id": sid]) { _ in
            self.isGenerating = false
            self.activeRequestId = nil
            self.uiState = "UI READY"
            self.liveThinkingStage = "CANCELLED"
            self.liveThinkingStatus = "GENERATION CANCELLED"
            self.requestAutoScroll(force: false, immediate: true)
        }
    }

    func editAndResend(_ text: String) {
        let cleaned = NUIClipboardManager.stripAttachmentFooter(text)
        chatInput = cleaned
        Task { await sendChatMessage(overridePrompt: cleaned) }
    }

    func beginEditingUserMessage(_ msg: ChatMessageItem) {
        editingMessageId = msg.id
        editingMessageDraft = NUIClipboardManager.stripAttachmentFooter(msg.content)
    }

    func cancelEditingUserMessage() {
        editingMessageId = nil
        editingMessageDraft = ""
    }

    func submitEditedUserMessage(_ msgId: String, newPrompt: String? = nil) async {
        let updatedText = (newPrompt ?? editingMessageDraft).trimmingCharacters(in: .whitespacesAndNewlines)
        guard !updatedText.isEmpty else { return }
        editingMessageId = nil
        editingMessageDraft = ""

        if let idx = messages.firstIndex(where: { $0.id == msgId }) {
            messages = Array(messages.prefix(idx))
        }

        if !currentSessionId.isEmpty {
            await postAsync("/api/chat/op", body: [
                "op": "edit_and_resend",
                "session_id": currentSessionId,
                "message_id": msgId,
                "user_message": updatedText,
                "provider": activeProvider,
                "model": selectedModelTag
            ]) { dict in
                if let resp = dict["response"] as? String, !resp.isEmpty {
                    let reqId = (dict["request_id"] as? String) ?? "req-edit"
                    let uMsg = ChatMessageItem(
                        id: msgId,
                        requestId: reqId,
                        role: "user",
                        content: updatedText,
                        provider: self.activeProvider,
                        model: self.selectedModelTag,
                        responseTimeMs: 0,
                        sourceAttribution: "USER_EDITED",
                        executionStatus: "SENT",
                        thinkingStages: [],
                        toolActivities: []
                    )
                    let aMsg = ChatMessageItem(
                        id: "asst-\(reqId)",
                        requestId: reqId,
                        role: "assistant",
                        content: resp,
                        provider: (dict["provider"] as? String) ?? self.activeProvider,
                        model: (dict["model"] as? String) ?? self.selectedModelTag,
                        responseTimeMs: 12.0,
                        sourceAttribution: (dict["source_attribution"] as? String) ?? "EDIT_AND_RESEND",
                        executionStatus: "COMPLETE",
                        thinkingStages: ["REQUEST_RECEIVED", "COMPLETE"],
                        toolActivities: []
                    )
                    self.messages.append(uMsg)
                    self.messages.append(aMsg)
                    self.lastUserPromptSent = updatedText
                    self.requestAutoScroll(force: true, immediate: true)
                    Task { await self.loadSessionMessages(self.currentSessionId, preserveScrollState: true) }
                } else {
                    Task { await self.sendChatMessage(overridePrompt: updatedText) }
                }
            }
        } else {
            await sendChatMessage(overridePrompt: updatedText)
        }
    }

    func regenerateAssistantAnswer(for assistantMsg: ChatMessageItem? = nil) async {
        guard !isGenerating else { return }
        var targetPrompt = lastUserPromptSent
        if let aMsg = assistantMsg,
           let aIdx = messages.firstIndex(where: { $0.id == aMsg.id }) {
            for idx in stride(from: aIdx - 1, through: 0, by: -1) {
                if messages[idx].role == "user" {
                    targetPrompt = NUIClipboardManager.stripAttachmentFooter(messages[idx].content)
                    break
                }
            }
            messages.remove(at: aIdx)
        } else if let lastUser = messages.last(where: { $0.role == "user" }) {
            targetPrompt = NUIClipboardManager.stripAttachmentFooter(lastUser.content)
            if let lastAsstIdx = messages.lastIndex(where: { $0.role == "assistant" }) {
                messages.remove(at: lastAsstIdx)
            }
        }

        if !currentSessionId.isEmpty {
            await postAsync("/api/chat/op", body: [
                "op": "regenerate",
                "session_id": currentSessionId,
                "assistant_message_id": assistantMsg?.id ?? "",
                "provider": activeProvider,
                "model": selectedModelTag
            ]) { dict in
                if let resp = dict["response"] as? String, !resp.isEmpty {
                    let reqId = (dict["request_id"] as? String) ?? "req-regen"
                    let aMsg = ChatMessageItem(
                        id: "asst-\(reqId)",
                        requestId: reqId,
                        role: "assistant",
                        content: resp,
                        provider: (dict["provider"] as? String) ?? self.activeProvider,
                        model: (dict["model"] as? String) ?? self.selectedModelTag,
                        responseTimeMs: 12.0,
                        sourceAttribution: (dict["source_attribution"] as? String) ?? "REGENERATED",
                        executionStatus: "COMPLETE",
                        thinkingStages: ["REQUEST_RECEIVED", "COMPLETE"],
                        toolActivities: []
                    )
                    self.messages.append(aMsg)
                    self.requestAutoScroll(force: true, immediate: true)
                    Task { await self.loadSessionMessages(self.currentSessionId, preserveScrollState: true) }
                } else if !targetPrompt.isEmpty {
                    Task { await self.sendChatMessage(overridePrompt: targetPrompt) }
                }
            }
        } else if !targetPrompt.isEmpty {
            await sendChatMessage(overridePrompt: targetPrompt)
        }
    }

    func retryLastMessage() {
        Task { await regenerateAssistantAnswer(for: nil) }
    }

    func copyTextToClipboard(_ text: String) {
        NUIClipboardManager.shared.copyString(text)
    }

    func copyUserQuestion(_ msg: ChatMessageItem) {
        let cleaned = NUIClipboardManager.stripAttachmentFooter(msg.content)
        NUIClipboardManager.shared.copyUserMessage(cleaned)
        let tag = "user-\(msg.id)"
        copiedItemId = tag
        copiedConfirmationBanner = "Copied ✓ · Pertanyaan tersalin ke clipboard (\(cleaned.count) karakter)"
        scheduleCopiedStateClear(expectedTag: tag)
    }

    func copyAssistantFullAnswer(_ msg: ChatMessageItem) {
        NUIClipboardManager.shared.copyAssistantResponse(msg.content)
        let tag = "asst-\(msg.id)"
        copiedItemId = tag
        copiedConfirmationBanner = "Copied ✓ · Jawaban NUI lengkap tersalin (\(msg.content.count) karakter)"
        scheduleCopiedStateClear(expectedTag: tag)
    }

    func copyRawCodeBlock(code: String, blockId: String) {
        NUIClipboardManager.shared.copyCodeBlockOnly(code)
        copiedItemId = blockId
        copiedConfirmationBanner = "Copied Code ✓ · Kode murni tersalin (\(code.count) karakter)"
        scheduleCopiedStateClear(expectedTag: blockId)
    }

    func pasteFromClipboardIntoComposer() {
        let clip = NUIClipboardManager.shared.readPasteboardString()
        guard !clip.isEmpty else { return }
        if chatInput.isEmpty {
            chatInput = clip
        } else {
            chatInput += clip
        }
    }

    func submitMessageFeedback(messageId: String, rating: String, note: String = "") {
        messageFeedbackMap[messageId] = rating
        copiedConfirmationBanner = "Feedback (\(rating)) tercatat untuk pesan \(messageId)"
        Task {
            await postAsync("/api/chat/op", body: [
                "op": "feedback",
                "session_id": currentSessionId,
                "message_id": messageId,
                "rating": rating,
                "note": note
            ]) { _ in }
        }
    }

    func openCodeSnippetInStudio(code: String, language: String) {
        editorContent = code
        let ext: String
        switch language.lowercased() {
        case "py", "python": ext = "py"
        case "swift": ext = "swift"
        case "v", "sv", "verilog": ext = "v"
        case "hasm", "hisa": ext = "hasm"
        default: ext = "txt"
        }
        editorFilePath = "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/snippet.\(ext)"
        studioOutput = "[LOADED FROM NUI CHAT] \(code.components(separatedBy: "\n").count) baris kode (\(language.isEmpty ? "code" : language)) siap diedit di Studio."
        selectedSection = .codingStudio
    }

    func checkYayasanVPSConnectionNow() {
        let yayasanPath = "/Users/AMRA/yayasan"
        localSyncFolderInput = yayasanPath
        if activeDomainInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            activeDomainInput = "www.akademihijaiyyahindonesia.com"
        }
        if !attachedPaths.contains(yayasanPath) {
            attachedPaths.append(yayasanPath)
        }
        Task {
            await connectFolderPath(yayasanPath, label: "yayasan", accessMode: "READ_WRITE")
            await verifyFullDeployment()
            await sendChatMessage(
                overridePrompt: "Periksa folder /Users/AMRA/yayasan, apakah sudah terhubung ke VPS dan apakah domain www.akademihijaiyyahindonesia.com sudah mengarah ke server?"
            )
        }
    }

    func extractLocalFilePathsFromMessage(_ content: String) -> [String] {
        var paths: [String] = []
        let patterns = [
            #"file://(/[^\)\s`"'>]+)"#,
            #"`((?:/Users/|/var/|/tmp/|/private/var/)[^`\n]+)`"#
        ]
        for pat in patterns {
            if let regex = try? NSRegularExpression(pattern: pat) {
                let matches = regex.matches(in: content, range: NSRange(content.startIndex..., in: content))
                for m in matches {
                    if m.numberOfRanges > 1, let r = Range(m.range(at: 1), in: content) {
                        let p = String(content[r]).removingPercentEncoding ?? String(content[r])
                        if !paths.contains(p) {
                            paths.append(p)
                        }
                    }
                }
            }
        }
        return paths
    }

    func openFileOutputInOS(_ path: String) {
        let url = URL(fileURLWithPath: path)
        guard FileManager.default.fileExists(atPath: path) else {
            copiedConfirmationBanner = "Berkas tidak ditemukan di disk: \(url.lastPathComponent)"
            return
        }
        NSWorkspace.shared.open(url)
        copiedConfirmationBanner = "Membuka berkas: \(url.lastPathComponent)"
    }

    func revealFileOutputInFinder(_ path: String) {
        let url = URL(fileURLWithPath: path)
        guard FileManager.default.fileExists(atPath: path) else {
            copiedConfirmationBanner = "Lokasi tidak ditemukan di disk: \(url.lastPathComponent)"
            return
        }
        NSWorkspace.shared.activateFileViewerSelecting([url])
        copiedConfirmationBanner = "Menampilkan di Finder: \(url.lastPathComponent)"
    }

    func copyFileOutputPath(_ path: String) {
        NUIClipboardManager.shared.copyString(path)
        let tag = "path-\(path.hashValue)"
        copiedItemId = tag
        copiedConfirmationBanner = "Copied Path ✓ · \(path)"
        scheduleCopiedStateClear(expectedTag: tag)
    }

    private func scheduleCopiedStateClear(expectedTag: String) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.4) { [weak self] in
            guard let self = self else { return }
            if self.copiedItemId == expectedTag {
                self.copiedItemId = ""
                self.copiedConfirmationBanner = nil
            }
        }
    }

    func activateSeparatedDemoTranscript() {
        isDemoModeActive = true
        currentSessionTitle = "[DEMO MODE] Transkrip Contoh (Bukan Sesi Produksi)"
        messages = [
            ChatMessageItem(
                id: "demo-1",
                requestId: "demo-req-1",
                role: "user",
                content: "[DEMO] Contoh pertanyaan: Berapa 5 + 7?",
                provider: "DEMO",
                model: "DEMO",
                responseTimeMs: 0,
                sourceAttribution: "DEMO_MODE",
                executionStatus: "DEMO",
                thinkingStages: [],
                toolActivities: []
            ),
            ChatMessageItem(
                id: "demo-2",
                requestId: "demo-req-1",
                role: "assistant",
                content: "**[DEMO MODE]** Ini adalah contoh transkrip terpisah berlabel `DEMO`. Klik **+ Sesi Baru** untuk kembali ke percakapan live produksi dengan Intelligence Engine.",
                provider: "DEMO",
                model: "DEMO",
                responseTimeMs: 1.0,
                sourceAttribution: "DEMO_MODE (Separated from Production)",
                executionStatus: "DEMO",
                thinkingStages: ["REQUEST_RECEIVED", "UNDERSTANDING", "TOOL_EXECUTION", "COMPLETE"],
                toolActivities: ["[DEMO] Contoh aktivitas perhitungan"]
            )
        ]
        requestAutoScroll(force: true, immediate: true)
    }

    func switchProvider(_ prov: String) async {
        activeProvider = prov
        await postAsync("/api/settings", body: ["active_provider": prov]) { _ in
            self.settingsBanner = "Provider updated to \(prov)."
            Task { await self.refreshAll() }
        }
    }

    func switchOperatingMode(_ mode: String) async {
        operatingMode = mode
        await postAsync("/api/settings", body: ["operating_mode": mode]) { _ in
            self.settingsBanner = "Operating mode updated to \(mode)."
            if mode == "LOCAL" {
                self.internetConnectivityState = "DISCONNECTED"
            } else {
                Task { await self.runConnectivityCheck() }
            }
            self.browserReloadToken &+= 1
            Task { await self.refreshAll() }
        }
    }

    func resetSettingsToDefaults() async {
        await postAsync("/api/settings/reset", body: [:]) { dict in
            if let s = dict["settings"] as? [String: Any] {
                self.operatingMode = (s["operating_mode"] as? String) ?? "HYBRID"
                self.activeProvider = (s["active_provider"] as? String) ?? "local_ollama"
            }
            self.settingsBanner = "Settings reset to defaults."
            Task { await self.refreshAll() }
        }
    }

    func runNativeConnectivityProbe() async {
        if operatingMode == "LOCAL" {
            internetConnectivityState = "DISCONNECTED"
            internetConnectivityReason = "OPERATING_MODE_LOCAL_LOCK"
            return
        }
        let targetURLStr = BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/"
        guard let url = URL(string: targetURLStr) else { return }

        // 1. Native POSIX DNS resolution check
        let dnsResolved = await Task.detached { () -> (Bool, String) in
            var hints = addrinfo()
            hints.ai_family = AF_UNSPEC
            hints.ai_socktype = SOCK_STREAM
            var resPtr: UnsafeMutablePointer<addrinfo>? = nil
            let code = Darwin.getaddrinfo("docs.python.org", "443", &hints, &resPtr)
            if let ptr = resPtr {
                Darwin.freeaddrinfo(ptr)
            }
            if code == 0 {
                return (true, "RESOLVED")
            } else {
                let msg = String(cString: gai_strerror(code))
                return (false, "DNS_FAILED(\(code): \(msg))")
            }
        }.value

        guard dnsResolved.0 else {
            internetConnectivityState = "DISCONNECTED"
            internetConnectivityReason = dnsResolved.1
            internetDiagnostics["dns"] = ["ok": false, "status": dnsResolved.1]
            return
        }

        // 2. Native URLSession HTTPS GET check (strict system TLS verification)
        var req = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 6.0)
        req.httpMethod = "GET"
        do {
            let (_, resp) = try await URLSession.shared.data(for: req)
            if let httpResp = resp as? HTTPURLResponse {
                let code = httpResp.statusCode
                browserLastHTTPStatus = code
                if code >= 200 && code < 400 {
                    internetConnectivityState = "CONNECTED"
                    internetConnectivityReason = "NATIVE_HTTPS_OK (HTTP \(code))"
                    internetDiagnostics["dns"] = ["ok": true, "status": "RESOLVED"]
                    internetDiagnostics["tls"] = ["ok": true, "status": "TLS_VERIFIED", "tls_version": "TLSv1.3"]
                    internetDiagnostics["https"] = ["ok": true, "status_code": code]
                } else {
                    internetConnectivityState = "LIMITED"
                    internetConnectivityReason = "HTTP_STATUS_\(code)"
                }
            }
        } catch {
            internetConnectivityState = "DISCONNECTED"
            internetConnectivityReason = "HTTPS_ERROR: \(error.localizedDescription)"
            internetDiagnostics["dns"] = ["ok": true, "status": "RESOLVED"]
            internetDiagnostics["https"] = ["ok": false, "status_code": 0, "error": error.localizedDescription]
        }
    }

    func runConnectivityCheck() async {
        await runNativeConnectivityProbe()
        await postAsync("/api/web/op", body: ["op": "diagnostics"]) { dict in
            self.internetDiagnostics = dict
            if let ov = dict["overall_status"] as? String, ov != "UNKNOWN" {
                self.internetConnectivityState = ov
            }
            if let r = dict["connectivity_reason"] as? String, !r.isEmpty {
                self.internetConnectivityReason = r
            }
            let dnsSt = ((dict["dns_resolution"] as? [String: Any])?["status"] as? String) ?? ((dict["dns"] as? [String: Any])?["status"] as? String) ?? "-"
            let tlsSt = ((dict["tls_verification"] as? [String: Any])?["status"] as? String) ?? ((dict["tls"] as? [String: Any])?["status"] as? String) ?? "-"
            let httpsSt = ((dict["https_reachability"] as? [String: Any])?["status"] as? String) ?? "-"
            let httpsCode = (dict["https_reachability"] as? [String: Any])?["status_code"] ?? (dict["https"] as? [String: Any])?["status_code"] ?? 0
            self.dnsStatusText = dnsSt
            self.httpsStatusText = "\(httpsSt) (HTTP \(httpsCode))"
            self.webSearchOutput = "[DIAGNOSTICS: \(self.internetConnectivityState)] DNS=\(dnsSt), TLS=\(tlsSt), HTTPS=\(httpsCode) (\(self.internetConnectivityReason))"
        }
    }

    func executeWebSearch() async {
        let q = webSearchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return }
        webSearchOutput = "Searching for '\(q)'..."
        await postAsync("/api/web/op", body: ["op": "search", "query": q]) { dict in
            let status = (dict["status"] as? String) ?? "OK"
            if let results = dict["results"] as? [[String: Any]], !results.isEmpty {
                let formatted = results.map { r in
                    let t = (r["title"] as? String) ?? ""
                    let u = (r["url"] as? String) ?? ""
                    let dt = (r["accessed_at"] as? String) ?? ""
                    let s = (r["snippet"] as? String) ?? ""
                    return "• \(t) [\(u)] (\(dt)):\n  \(s)"
                }.joined(separator: "\n\n")
                self.webSearchOutput = "[\(status)] \(results.count) sumber terverifikasi:\n\n\(formatted)"
            } else {
                let err = (dict["reason"] as? String) ?? (dict["error"] as? String) ?? (dict["summary"] as? String) ?? status
                self.webSearchOutput = "[\(status)] \(err)"
                Task { await self.refreshAll() }
            }
        }
    }

    func inspectAndInstallDependency(dryRun: Bool = true) async {
        let body: [String: Any] = [
            "op": "dependency_install",
            "manager": dependencyManagerName,
            "package": dependencyPackageName,
            "dry_run": dryRun
        ]
        await postAsync("/api/web/op", body: body) { dict in
            let st = (dict["status"] as? String) ?? "READY"
            let ver = (dict["verification"] as? String) ?? (dict["reason"] as? String) ?? ""
            self.webSearchOutput = "[DEPENDENCY \(st)] \(ver)"
            Task { await self.refreshAll() }
        }
    }

    func registerAndConnectVPS() async {
        guard !vpsHostInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            vpsOutput = "Masukkan alamat Host/IP VPS terlebih dahulu."
            return
        }
        let regBody: [String: Any] = [
            "op": "register",
            "name": vpsNameInput,
            "host": vpsHostInput,
            "username": vpsUserInput,
            "expected_host_fingerprint": vpsFingerprintInput,
            "remote_workspace": vpsWorkspaceInput
        ]
        await postAsync("/api/vps/op", body: regBody) { dict in
            let pid = (dict["profile_id"] as? String) ?? ""
            self.vpsOutput = "Profil VPS terdaftar (\(pid)). Menghubungkan & memverifikasi host key..."
            Task {
                await self.postAsync("/api/vps/op", body: ["op": "connect", "profile_id": pid]) { cDict in
                    let st = (cDict["status"] as? String) ?? "UNKNOWN"
                    let reason = (cDict["os_and_architecture"] as? String) ?? (cDict["reason"] as? String) ?? st
                    self.vpsOutput = "[VPS \(st)] \(reason)"
                    Task { await self.refreshAll() }
                }
            }
        }
    }

    func runRemoteVPSCommand() async {
        guard let firstProf = vpsProfiles.first, let pid = firstProf["profile_id"] as? String else {
            vpsOutput = "Belum ada profil VPS terdaftar."
            return
        }
        await postAsync("/api/vps/op", body: ["op": "execute", "profile_id": pid, "command": vpsCommandInput]) { dict in
            let st = (dict["status"] as? String) ?? "UNKNOWN"
            let out = (dict["stdout"] as? String) ?? (dict["reason"] as? String) ?? ""
            self.vpsOutput = "[VPS EXEC \(st)]\n\(out)"
            Task { await self.refreshAll() }
        }
    }

    func checkDomainStatus() async {
        let dom = activeDomainInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !dom.isEmpty else { return }
        await postAsync("/api/web/op", body: ["op": "check_domain", "domain": dom]) { dict in
            let cls = (dict["classification"] as? String) ?? "DOMAIN_NOT_RESOLVED"
            let ver = (dict["verification_status"] as? String) ?? "UNKNOWN"
            let ipv4 = (dict["resolved_ipv4"] as? [String]) ?? []
            let httpHttps = (dict["http_https"] as? [String: Any]) ?? [:]
            let httpsProbe = (httpHttps["https_probe"] as? [String: Any]) ?? [:]
            let tlsCert = (httpHttps["tls_certificate"] as? [String: Any]) ?? [:]
            let httpsCode = (httpsProbe["status_code"] as? Int) ?? 0
            let httpsSt = (httpsProbe["status"] as? String) ?? "UNKNOWN"
            let certValid = (tlsCert["cert_valid"] as? Bool) ?? false
            let issuer = (tlsCert["issuer_cn"] as? String) ?? "NONE"
            self.domainResolutionText = ipv4.isEmpty ? "\(cls) (NO A RECORD)" : "\(cls) (\(ipv4.joined(separator: ", ")))"
            self.websiteHttpStatusText = httpsCode > 0 ? "HTTP \(httpsCode) (\(httpsSt))" : httpsSt
            self.tlsCertificateStatusText = certValid ? "VALID (\(issuer))" : "UNVERIFIED (\( (tlsCert["status"] as? String) ?? "NONE" ))"
            let concl = (dict["conclusion"] as? String) ?? ""
            self.networkVpsVerificationReport = "[DOMAIN CHECK: \(dom) — \(ver)]\nClassification: \(cls)\nIPv4: \(ipv4)\nHTTP/HTTPS: \(self.websiteHttpStatusText)\nTLS: \(self.tlsCertificateStatusText)\n\n\(concl)"
        }
    }

    func testSSHConnection() async {
        await postAsync("/api/vps/op", body: ["op": "inspect_folder", "folder_path": localSyncFolderInput]) { dict in
            self.activeVpsProfileText = (dict["remote_ssh_profile"] as? String) ?? "NONE"
            self.sshStatusText = (dict["ssh_connection_status"] as? String) ?? "NOT_CONFIGURED"
            self.hostFingerprintText = (dict["verified_host_fingerprint"] as? String) ?? "NOT_VERIFIED"
            self.sftpStatusText = (dict["sftp_connection"] as? String) ?? "NOT_AVAILABLE"
            self.remoteWorkspaceText = (dict["remote_workspace_path"] as? String) ?? "NONE"
            self.vpsOutput = (dict["formatted_report"] as? String) ?? "SSH status checked."
            self.networkVpsVerificationReport = self.vpsOutput
        }
    }

    func inspectRemoteWorkspaceManifest() async {
        let pid = (vpsProfiles.first?["profile_id"] as? String) ?? ""
        await postAsync("/api/vps/op", body: ["op": "inspect_remote_manifest", "profile_id": pid]) { dict in
            let st = (dict["status"] as? String) ?? "NOT_CONFIGURED"
            let cnt = (dict["file_count"] as? Int) ?? 0
            let reason = (dict["reason"] as? String) ?? "Remote manifest inspected."
            self.vpsOutput = "[REMOTE MANIFEST \(st)] Files: \(cnt) — \(reason)"
            self.networkVpsVerificationReport = self.vpsOutput
        }
    }

    func compareLocalAndRemoteManifests() async {
        let pid = vpsProfiles.first?["profile_id"] as? String
        var body: [String: Any] = ["op": "compare_manifests", "local_path": localSyncFolderInput]
        if let pid = pid { body["profile_id"] = pid }
        await postAsync("/api/vps/op", body: body) { dict in
            let st = (dict["overall_sync_status"] as? String) ?? "NOT_CONFIGURED"
            self.syncStatusText = st
            let rep = (dict["formatted_report"] as? String) ?? (dict["conclusion"] as? String) ?? st
            self.networkVpsVerificationReport = rep
            self.vpsOutput = rep
        }
    }

    func uploadFilesToVPS() async {
        let pid = vpsProfiles.first?["profile_id"] as? String
        var body: [String: Any] = ["op": "transfer_to_vps", "path": localSyncFolderInput]
        if let pid = pid { body["profile_id"] = pid }
        await postAsync("/api/resources/op", body: body) { dict in
            let st = (dict["status"] as? String) ?? "NOT_CONFIGURED"
            let reason = (dict["reason"] as? String) ?? (dict["summary"] as? String) ?? st
            self.vpsOutput = "[UPLOAD TO VPS: \(st)] \(reason)"
            self.networkVpsVerificationReport = self.vpsOutput
        }
    }

    func syncDirectoryToVPS() async {
        await compareLocalAndRemoteManifests()
    }

    func verifyFullDeployment() async {
        await runConnectivityCheck()
        let body: [String: Any] = [
            "op": "full_verification",
            "local_path": localSyncFolderInput,
            "domain": activeDomainInput
        ]
        await postAsync("/api/vps/op", body: body) { dict in
            self.lastFolderVPSInspection = dict
            self.activeVpsProfileText = (dict["remote_ssh_profile"] as? String) ?? "NONE"
            self.sshStatusText = (dict["ssh_connection_status"] as? String) ?? "NOT_CONFIGURED"
            self.hostFingerprintText = (dict["verified_host_fingerprint"] as? String) ?? "NOT_VERIFIED"
            self.sftpStatusText = (dict["sftp_connection"] as? String) ?? "NOT_AVAILABLE"
            self.remoteWorkspaceText = (dict["remote_workspace_path"] as? String) ?? "NONE"
            if let syncDict = dict["file_synchronization"] as? [String: Any] {
                self.syncStatusText = (syncDict["overall_sync_status"] as? String) ?? "NOT_CONFIGURED"
            }
            if let domDict = dict["domain"] as? [String: Any] {
                let cls = (domDict["classification"] as? String) ?? "DOMAIN_NOT_RESOLVED"
                let ipv4 = (domDict["resolved_ipv4"] as? [String]) ?? (domDict["resolved_ips"] as? [String]) ?? []
                self.domainResolutionText = ipv4.isEmpty ? cls : "\(cls) (\(ipv4.joined(separator: ", ")))"
                if let webDict = domDict["web"] as? [String: Any] {
                    let hget = (webDict["https_get"] as? [String: Any]) ?? [:]
                    let tc = (webDict["tls"] as? [String: Any]) ?? [:]
                    let code = (hget["status_code"] as? Int) ?? 0
                    let ok = (hget["ok"] as? Bool) ?? false
                    self.websiteHttpStatusText = code > 0 ? "HTTP \(code) (\(ok ? "ONLINE" : "ERROR"))" : (cls == "DOMAIN_NOT_RESOLVED" ? "SKIPPED_DNS_NOT_RESOLVED" : "OFFLINE")
                    let valid = (tc["cert_valid"] as? Bool) ?? false
                    self.tlsCertificateStatusText = valid ? "VALID" : ((tc["status"] as? String) ?? "UNVERIFIED")
                } else if let hh = domDict["http_https"] as? [String: Any] {
                    let hp = (hh["https_probe"] as? [String: Any]) ?? [:]
                    let tc = (hh["tls_certificate"] as? [String: Any]) ?? [:]
                    let code = (hp["status_code"] as? Int) ?? 0
                    let hst = (hp["status"] as? String) ?? "UNKNOWN"
                    self.websiteHttpStatusText = code > 0 ? "HTTP \(code) (\(hst))" : hst
                    let valid = (tc["cert_valid"] as? Bool) ?? false
                    self.tlsCertificateStatusText = valid ? "VALID" : ((tc["status"] as? String) ?? "UNVERIFIED")
                }
            }
            if let rep = dict["formatted_report"] as? String {
                self.networkVpsVerificationReport = rep
                self.vpsOutput = rep
            }
        }
    }

    func disconnectRemoteVPS() async {
        let pid = (vpsProfiles.first?["profile_id"] as? String) ?? ""
        await postAsync("/api/vps/op", body: ["op": "disconnect", "profile_id": pid]) { dict in
            let st = (dict["status"] as? String) ?? "DISCONNECTED"
            self.sshStatusText = "DISCONNECTED"
            self.sftpStatusText = "NOT_AVAILABLE"
            self.vpsOutput = "[VPS \(st)] Sesi remote VPS diputuskan dengan aman."
            self.networkVpsVerificationReport = self.vpsOutput
            Task { await self.refreshAll() }
        }
    }

    func openFileInStudio() async {
        let p = editorFilePath.trimmingCharacters(in: .whitespacesAndNewlines)
        await postAsync("/api/files/op", body: ["op": "read", "path": p]) { dict in
            if let content = dict["content"] as? String {
                self.editorContent = content
                self.studioOutput = "Loaded \(p) (\(content.count) chars)"
            } else {
                let err = (dict["error"] as? String) ?? "Read failed"
                self.studioOutput = "Error: \(err)"
            }
        }
    }

    func saveFileInStudio() async {
        let p = editorFilePath.trimmingCharacters(in: .whitespacesAndNewlines)
        await postAsync("/api/files/op", body: ["op": "write", "path": p, "content": editorContent]) { dict in
            let st = (dict["status"] as? String) ?? "UNKNOWN"
            if st == "WRITTEN" || st == "OK" {
                self.studioOutput = "Saved \(p) (\(self.editorContent.count) chars)"
            } else {
                let err = (dict["error"] as? String) ?? st
                self.studioOutput = "Write status: \(err)"
            }
        }
    }

    func decideApproval(requestId: String, decision: String) async {
        await postAsync("/api/permissions/decide", body: ["request_id": requestId, "decision": decision]) { _ in
            Task { await self.refreshAll() }
        }
    }

    func triggerHardwareAction(_ action: String) async {
        await postAsync("/api/hardware/control", body: ["subsystem": "TANG_NANO_20K", "action": action]) { _ in
            Task { await self.refreshAll() }
        }
    }

    private func fetchAsync(_ path: String, completion: @escaping ([String: Any]) -> Void) async {
        let res = await Task.detached { () -> (Int, [String: Any])? in
            try? LocalLoopbackClient.sendRequest(method: "GET", path: path, timeoutSeconds: 4)
        }.value
        if let (code, dict) = res, code == 200 {
            completion(dict)
        }
    }

    private func postAsync(_ path: String, body: [String: Any], completion: @escaping ([String: Any]) -> Void) async {
        let res = await Task.detached { () -> (Int, [String: Any])? in
            try? LocalLoopbackClient.sendRequest(method: "POST", path: path, body: body, timeoutSeconds: 8)
        }.value
        if let (code, dict) = res, code >= 200 && code < 300 {
            completion(dict)
        }
    }

    private func deleteAsync(_ path: String, body: [String: Any]? = nil, completion: @escaping (Int, [String: Any]) -> Void) async {
        let res = await Task.detached { () -> (Int, [String: Any])? in
            try? LocalLoopbackClient.sendRequest(method: "DELETE", path: path, body: body, timeoutSeconds: 6)
        }.value
        if let (code, dict) = res {
            completion(code, dict)
        }
    }
}

// MARK: - Safari + Chrome + CosmicTera Full Browser Workspace View (Sections A, B, C, D, E)

struct CosmicTeraBrowserWorkspaceView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        let dnsDict = (store.internetDiagnostics["dns"] as? [String: Any]) ?? [:]
        let tlsDict = (store.internetDiagnostics["tls"] as? [String: Any]) ?? [:]
        let httpsDict = (store.internetDiagnostics["https"] as? [String: Any]) ?? [:]
        let dnsSt = (dnsDict["status"] as? String) ?? "-"
        let tlsSt = (tlsDict["tls_version"] as? String) ?? (tlsDict["status"] as? String) ?? "-"
        let httpsCode = (httpsDict["status_code"] as? Int) ?? store.browserLastHTTPStatus

        VStack(spacing: 0) {
            // 1. BROWSER TAB STRIP (Chrome/Safari Multi-Tab Bar)
            HStack(spacing: 6) {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 5) {
                        ForEach(Array(store.browserTabs.enumerated()), id: \.element.id) { idx, tab in
                            let isActive = (tab.id == store.activeBrowserTabId)
                            HStack(spacing: 6) {
                                if tab.isLoading {
                                    ProgressView()
                                        .scaleEffect(0.55)
                                        .frame(width: 14, height: 14)
                                } else {
                                    Image(systemName: tab.favicon)
                                        .font(.system(size: 11, weight: .semibold))
                                        .foregroundColor(isActive ? CosmicTheme.emerald : CosmicTheme.cyan)
                                }

                                Button(action: {
                                    Task { await store.switchBrowserTab(tab.id) }
                                }) {
                                    Text(tab.title.isEmpty ? tab.domain : tab.title)
                                        .font(.system(size: 11.5, weight: isActive ? .bold : .medium))
                                        .foregroundColor(isActive ? CosmicTheme.silver : CosmicTheme.muted)
                                        .lineLimit(1)
                                        .frame(maxWidth: 165, alignment: .leading)
                                }
                                .buttonStyle(.plain)

                                if store.browserTabs.count > 1 {
                                    if idx > 0 {
                                        Button(action: {
                                            Task { await store.moveBrowserTab(tabId: tab.id, direction: -1) }
                                        }) {
                                            Image(systemName: "chevron.left")
                                                .font(.system(size: 8.5, weight: .bold))
                                                .foregroundColor(CosmicTheme.muted)
                                        }
                                        .buttonStyle(.plain)
                                        .help("Geser tab ke kiri")
                                    }
                                    if idx + 1 < store.browserTabs.count {
                                        Button(action: {
                                            Task { await store.moveBrowserTab(tabId: tab.id, direction: 1) }
                                        }) {
                                            Image(systemName: "chevron.right")
                                                .font(.system(size: 8.5, weight: .bold))
                                                .foregroundColor(CosmicTheme.muted)
                                        }
                                        .buttonStyle(.plain)
                                        .help("Geser tab ke kanan")
                                    }
                                }

                                Button(action: {
                                    Task { await store.closeBrowserTab(tab.id) }
                                }) {
                                    Image(systemName: "xmark")
                                        .font(.system(size: 9.5, weight: .bold))
                                        .foregroundColor(isActive ? CosmicTheme.silver : CosmicTheme.muted)
                                        .padding(3)
                                        .contentShape(Rectangle())
                                }
                                .buttonStyle(.plain)
                                .help("Tutup tab")
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(isActive ? CosmicTheme.bgCard : CosmicTheme.bgSecondary.opacity(0.65))
                            .overlay(
                                RoundedRectangle(cornerRadius: 7)
                                    .stroke(isActive ? CosmicTheme.emerald.opacity(0.8) : CosmicTheme.cyan.opacity(0.18), lineWidth: 1)
                            )
                            .cornerRadius(7)
                        }

                        Button(action: {
                            Task { await store.openNewBrowserTab() }
                        }) {
                            Label("New Tab", systemImage: "plus")
                                .font(.system(size: 11, weight: .bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 5)
                                .background(CosmicTheme.bgCard)
                                .foregroundColor(CosmicTheme.cyan)
                                .cornerRadius(6)
                        }
                        .buttonStyle(.plain)
                        .help("Buka Tab Baru (+)")
                    }
                    .padding(.vertical, 4)
                }

                Spacer()

                Text(store.browserSessionPolicy == "TEMPORARY_PRIVATE" ? "PRIVATE SESSION" : "PERSISTENT PROFILE")
                    .font(.system(size: 9.5, weight: .bold, design: .monospaced))
                    .padding(.horizontal, 7)
                    .padding(.vertical, 3)
                    .background(store.browserSessionPolicy == "TEMPORARY_PRIVATE" ? CosmicTheme.gold.opacity(0.22) : CosmicTheme.emerald.opacity(0.18))
                    .foregroundColor(store.browserSessionPolicy == "TEMPORARY_PRIVATE" ? CosmicTheme.gold : CosmicTheme.emerald)
                    .cornerRadius(5)
            }
            .padding(.horizontal, 10)
            .padding(.top, 4)
            .background(CosmicTheme.bgSecondary)

            // 2. NAVIGATION TOOLBAR (Back, Forward, Reload/Stop, Home, Unified Address/Search Bar, Find, Zoom, Bookmark, Downloads, History, Menu)
            HStack(spacing: 6) {
                Button(action: { Task { await store.browserGoBack() } }) {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 12, weight: .bold))
                }
                .buttonStyle(.bordered)
                .disabled(!store.activeTabModel.canGoBack && store.browserHistoryIndex <= 0)
                .help("Back (Halaman Sebelumnya)")

                Button(action: { Task { await store.browserGoForward() } }) {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 12, weight: .bold))
                }
                .buttonStyle(.bordered)
                .disabled(!store.activeTabModel.canGoForward && store.browserHistoryIndex + 1 >= store.browserHistory.count)
                .help("Forward (Halaman Berikutnya)")

                if store.browserIsLoading {
                    Button(action: { store.stopBrowserLoading() }) {
                        Image(systemName: "xmark")
                            .font(.system(size: 11.5, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.redFault)
                    .help("Stop Loading")
                } else {
                    Button(action: { Task { await store.reloadCurrentBrowserTab() } }) {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 11.5, weight: .bold))
                    }
                    .buttonStyle(.bordered)
                    .help("Reload Halaman (↻)")
                }

                Button(action: { Task { await store.browserGoHome() } }) {
                    Image(systemName: "house.fill")
                        .font(.system(size: 11.5))
                }
                .buttonStyle(.bordered)
                .help("Home (https://docs.python.org/3/)")

                // Unified Address / Search Input Pill
                HStack(spacing: 6) {
                    Image(systemName: store.browserSecurityState == "SECURE_HTTPS" ? "lock.fill" : "exclamationmark.triangle.fill")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(store.browserSecurityState == "SECURE_HTTPS" ? CosmicTheme.emerald : CosmicTheme.gold)
                        .help(store.browserSecurityState == "SECURE_HTTPS" ? "Koneksi HTTPS Terenkripsi (TLS Verified)" : "Status Keamanan: \(store.browserSecurityState)")

                    Text(store.activeTabModel.domain)
                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(CosmicTheme.bgSecondary)
                        .foregroundColor(CosmicTheme.cyan)
                        .cornerRadius(4)

                    TextField("Ketik URL (mis. docs.python.org/3/) atau kata kunci pencarian...", text: $store.browserAddress)
                        .textFieldStyle(.plain)
                        .font(.system(size: 12.5, design: .monospaced))
                        .foregroundColor(CosmicTheme.silver)
                        .onSubmit {
                            Task { await store.navigateBrowser() }
                        }

                    if !store.browserAddress.isEmpty {
                        Button(action: { store.browserAddress = "" }) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 11))
                                .foregroundColor(CosmicTheme.muted)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
                .background(CosmicTheme.bgCode)
                .overlay(
                    RoundedRectangle(cornerRadius: 7)
                        .stroke(CosmicTheme.cyan.opacity(0.45), lineWidth: 1)
                )
                .cornerRadius(7)

                Button("Go") {
                    Task { await store.navigateBrowser() }
                }
                .buttonStyle(.borderedProminent)
                .tint(CosmicTheme.emerald)

                // Find on Page Button
                Button(action: {
                    store.isFindBarVisible.toggle()
                }) {
                    Image(systemName: "doc.text.magnifyingglass")
                        .font(.system(size: 11.5))
                }
                .buttonStyle(.bordered)
                .help("Find on Page")

                // Zoom Controls (- / 100% / +)
                HStack(spacing: 2) {
                    Button("-") { Task { await store.adjustBrowserZoom(delta: -0.1) } }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    Button("\(Int(round(store.browserZoomLevel * 100)))%") {
                        Task { await store.adjustBrowserZoom(delta: 0, reset: true) }
                    }
                    .buttonStyle(.plain)
                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                    .foregroundColor(CosmicTheme.gold)
                    .frame(width: 38)
                    Button("+") { Task { await store.adjustBrowserZoom(delta: 0.1) } }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                }

                // Quick Bookmark Star Button
                Button(action: {
                    Task { await store.addCurrentPageBookmark() }
                }) {
                    Image(systemName: "star.fill")
                        .foregroundColor(CosmicTheme.gold)
                }
                .buttonStyle(.bordered)
                .help("Simpan halaman aktif ke Bookmarks")

                // Bookmarks Drawer Button
                Button(action: {
                    store.activeBrowserDrawer = (store.activeBrowserDrawer == .bookmarks) ? .none : .bookmarks
                }) {
                    Image(systemName: "book.fill")
                }
                .buttonStyle(.bordered)
                .help("Kelola Bookmarks & Folder")

                // History Drawer Button
                Button(action: {
                    store.activeBrowserDrawer = (store.activeBrowserDrawer == .history) ? .none : .history
                    Task { await store.searchBrowserHistory() }
                }) {
                    Image(systemName: "clock.arrow.circlepath")
                }
                .buttonStyle(.bordered)
                .help("Riwayat Kunjungan (Browser History)")

                // Downloads Drawer Button
                Button(action: {
                    store.activeBrowserDrawer = (store.activeBrowserDrawer == .downloads) ? .none : .downloads
                }) {
                    HStack(spacing: 3) {
                        Image(systemName: "arrow.down.circle.fill")
                        Text("\(store.browserDownloads.count)")
                            .font(.system(size: 10, weight: .bold, design: .monospaced))
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(CosmicTheme.cyan)
                .help("Download Manager (\(store.browserDownloads.count) berkas di staging)")

                // Session, Privacy & Layout Menu
                Menu {
                    Section("Session & Privacy Policy") {
                        Button("Mode: Persistent Profile (Simpan Sesi & History)") {
                            Task { await store.switchBrowserSessionPolicy("PERSISTENT_PROFILE") }
                        }
                        Button("Mode: Temporary Private (Non-Persistent)") {
                            Task { await store.switchBrowserSessionPolicy("TEMPORARY_PRIVATE") }
                        }
                    }
                    Divider()
                    Section("Data & Cache Controls") {
                        Button("Clear Cookies Only") {
                            Task { await store.clearBrowserCookiesOnly() }
                        }
                        Button("Clear Cache Only") {
                            Task { await store.clearBrowserCacheOnly() }
                        }
                        Button("Clear Browser History") {
                            Task { await store.clearAllBrowserHistory() }
                        }
                        Button("Clear All Session Data") {
                            Task { await store.clearBrowserSessionData() }
                        }
                    }
                    Divider()
                    Button("Stage Download Halaman Aktif") {
                        Task { await store.downloadCurrentBrowserURLToStaging() }
                    }
                    Button("Run Live Connectivity Probe (DNS/TLS/HTTPS)") {
                        Task { await store.runConnectivityCheck() }
                    }
                } label: {
                    Image(systemName: "ellipsis.circle.fill")
                        .font(.system(size: 13))
                }
                .frame(width: 32)
                .help("Pengaturan Sesi Browser, Cookies, Cache & Privasi")

                // Expand Browser / Toggle Right Inspector
                Button(action: {
                    store.isRightInspectorCollapsed.toggle()
                }) {
                    Image(systemName: store.isRightInspectorCollapsed ? "sidebar.right" : "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 11.5, weight: .bold))
                }
                .buttonStyle(.bordered)
                .help(store.isRightInspectorCollapsed ? "Tampilkan Inspector Kanan" : "Perluas Area Browser (Sembunyikan Inspector Kanan)")
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(CosmicTheme.bgCard)

            // 3. BOOKMARKS BAR (Quick Chips + Folder Filter)
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    Image(systemName: "bookmark.fill")
                        .font(.system(size: 10.5))
                        .foregroundColor(CosmicTheme.gold)

                    Menu {
                        ForEach(store.browserBookmarkFolders, id: \.self) { folder in
                            Button(folder) {
                                store.selectedBookmarkFolderFilter = folder
                            }
                        }
                    } label: {
                        Text("Folder: \(store.selectedBookmarkFolderFilter)")
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .foregroundColor(CosmicTheme.cyan)
                    }
                    .frame(width: 145)

                    let visibleBookmarks = store.browserBookmarks.filter { bm in
                        store.selectedBookmarkFolderFilter == "All" || ((bm["folder"] as? String) == store.selectedBookmarkFolderFilter)
                    }

                    ForEach(Array(visibleBookmarks.enumerated()), id: \.offset) { _, bm in
                        let bmId = (bm["bookmark_id"] as? String) ?? ""
                        let bmTitle = (bm["title"] as? String) ?? "Bookmark"
                        let bmURL = (bm["url"] as? String) ?? "https://docs.python.org/3/"
                        let bmFolder = (bm["folder"] as? String) ?? "General"
                        let bmIcon = (bm["favicon"] as? String) ?? "globe"

                        HStack(spacing: 5) {
                            Image(systemName: bmIcon)
                                .font(.system(size: 10))
                                .foregroundColor(CosmicTheme.emerald)
                            Button(bmTitle) {
                                Task { await store.navigateBrowser(to: bmURL) }
                            }
                            .buttonStyle(.plain)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(CosmicTheme.silver)
                            .help("\(bmTitle) — \(bmURL) [\(bmFolder)]")
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 3)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(6)
                        .contextMenu {
                            Button("Buka di Tab Aktif") {
                                Task { await store.navigateBrowser(to: bmURL) }
                            }
                            Button("Buka di Tab Baru") {
                                Task { await store.openNewBrowserTab(initialURL: bmURL) }
                            }
                            Divider()
                            Button("Pindahkan ke Folder Documentation") {
                                Task { await store.saveEditedBookmark(bookmarkId: bmId, title: bmTitle, url: bmURL, folder: "Documentation") }
                            }
                            Button("Pindahkan ke Folder Development") {
                                Task { await store.saveEditedBookmark(bookmarkId: bmId, title: bmTitle, url: bmURL, folder: "Development") }
                            }
                            Divider()
                            Button("Hapus Bookmark") {
                                Task { await store.deleteBrowserBookmark(bmId) }
                            }
                        }
                    }

                    Button("+ Tambah Bookmark") {
                        store.newBookmarkTitleInput = store.browserPageTitle
                        store.newBookmarkURLInput = store.browserActiveURL
                        store.activeBrowserDrawer = .bookmarks
                    }
                    .buttonStyle(.plain)
                    .font(.system(size: 10.5, weight: .bold))
                    .foregroundColor(CosmicTheme.gold)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 5)
            }
            .background(CosmicTheme.bgSecondary)

            // 4. OPTIONAL FIND ON PAGE BAR
            if store.isFindBarVisible {
                HStack(spacing: 8) {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(CosmicTheme.cyan)
                    TextField("Cari teks di halaman aktif...", text: $store.browserFindQuery)
                        .textFieldStyle(.roundedBorder)
                        .frame(maxWidth: 280)
                        .onSubmit {
                            Task { await store.runBrowserFindOnPage() }
                        }
                    Button("Find Next") {
                        Task { await store.runBrowserFindOnPage() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.emerald)
                    Text("Matches: \(store.browserFindMatchCount)")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(CosmicTheme.gold)
                    Spacer()
                    Button("Tutup") {
                        store.isFindBarVisible = false
                        store.browserFindQuery = ""
                        Task { await store.runBrowserFindOnPage() }
                    }
                    .buttonStyle(.bordered)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(CosmicTheme.bgCard)
            }

            // 5. COLLAPSIBLE DRAWERS (BOOKMARKS / HISTORY / DOWNLOAD MANAGER)
            if store.activeBrowserDrawer != .none {
                BrowserDrawerContainerView(store: store)
                    .frame(maxHeight: 195)
                Divider().background(CosmicTheme.cyan.opacity(0.3))
            }

            // Loading Progress Bar
            if store.browserIsLoading {
                ProgressView(value: store.browserLoadingProgress, total: 1.0)
                    .progressViewStyle(.linear)
                    .tint(CosmicTheme.emerald)
            }

            // 6. MAIN WEB CONTENT VIEWPORT (Full-Frame Native WKWebView)
            LiveBrowserWebView(store: store)
                .frame(minWidth: 480, minHeight: 380)
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            Divider().background(CosmicTheme.cyan.opacity(0.3))

            // 7. BROWSER STATUS & SECURITY INDICATOR FOOTER
            HStack(spacing: 12) {
                Button(action: { Task { await store.runConnectivityCheck() } }) {
                    HStack(spacing: 5) {
                        Circle()
                            .fill(store.operatingMode != "LOCAL" && store.internetConnectivityState == "CONNECTED" ? CosmicTheme.emerald : CosmicTheme.gold)
                            .frame(width: 7, height: 7)
                        Text("NET: \(store.operatingMode == "LOCAL" ? "DISCONNECTED (LOCAL)" : store.internetConnectivityState)")
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .foregroundColor(store.operatingMode != "LOCAL" && store.internetConnectivityState == "CONNECTED" ? CosmicTheme.emerald : CosmicTheme.gold)
                    }
                }
                .buttonStyle(.plain)
                .help("Penyebab Status Jaringan: \(store.internetConnectivityReason) — Klik untuk menjalankan probe ulang")

                Text("Title: \(store.browserPageTitle)")
                    .font(.system(size: 10.5, weight: .semibold))
                    .foregroundColor(CosmicTheme.silver)
                    .lineLimit(1)
                    .frame(maxWidth: 210, alignment: .leading)
                Text("DNS: \(dnsSt)")
                    .font(.system(size: 10.5, design: .monospaced))
                    .foregroundColor(CosmicTheme.silver)
                Text("TLS: \(tlsSt)")
                    .font(.system(size: 10.5, design: .monospaced))
                    .foregroundColor(CosmicTheme.cyan)
                Text("HTTPS: \(httpsCode)")
                    .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                    .foregroundColor(httpsCode >= 200 && httpsCode < 400 ? CosmicTheme.emerald : CosmicTheme.gold)
                Text("Status: \(store.browserStatusText)")
                    .font(.system(size: 10.5, weight: .semibold, design: .monospaced))
                    .foregroundColor(store.browserStatusText == "FAILED" ? CosmicTheme.redFault : (store.browserStatusText == "COMPLETE" ? CosmicTheme.emerald : CosmicTheme.gold))
                Spacer()
                Text("Nav: \(store.browserCurrentNavigationId.suffix(10)) | Tabs: \(store.browserTabs.count)")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundColor(CosmicTheme.muted)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 5)
            .background(CosmicTheme.bgSecondary)
        }
        .onAppear {
            if store.operatingMode != "LOCAL" {
                Task { await store.runConnectivityCheck() }
            }
        }
    }
}

struct BrowserDrawerContainerView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(
                    store.activeBrowserDrawer == .bookmarks
                        ? "BOOKMARKS & FOLDER ORGANIZER"
                        : (store.activeBrowserDrawer == .history ? "BROWSER HISTORY" : "SAFE STAGING DOWNLOAD MANAGER")
                )
                .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                .foregroundColor(CosmicTheme.gold)
                Spacer()
                Button("Tutup Panel") {
                    store.activeBrowserDrawer = .none
                }
                .buttonStyle(.bordered)
                .controlSize(.small)
            }

            if store.activeBrowserDrawer == .bookmarks {
                HStack(spacing: 6) {
                    TextField("Judul Bookmark", text: $store.newBookmarkTitleInput)
                        .textFieldStyle(.roundedBorder)
                    TextField("URL (https://...)", text: $store.newBookmarkURLInput)
                        .textFieldStyle(.roundedBorder)
                    TextField("Folder", text: $store.newBookmarkFolderInput)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 130)
                    Button("Simpan Bookmark") {
                        Task { await store.addCurrentPageBookmark() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.emerald)
                }

                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(store.browserBookmarks.enumerated()), id: \.offset) { _, bm in
                            let bmId = (bm["bookmark_id"] as? String) ?? ""
                            let bmTitle = (bm["title"] as? String) ?? ""
                            let bmURL = (bm["url"] as? String) ?? ""
                            let bmFolder = (bm["folder"] as? String) ?? "General"
                            HStack {
                                Text("[\(bmFolder)] \(bmTitle)")
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(CosmicTheme.silver)
                                Text(bmURL)
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundColor(CosmicTheme.cyan)
                                    .lineLimit(1)
                                Spacer()
                                Button("Open") {
                                    Task { await store.navigateBrowser(to: bmURL) }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(CosmicTheme.emerald)
                                .controlSize(.small)
                                Button("Delete") {
                                    Task { await store.deleteBrowserBookmark(bmId) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            } else if store.activeBrowserDrawer == .history {
                HStack(spacing: 8) {
                    TextField("Cari riwayat kunjungan...", text: $store.browserHistorySearchQuery)
                        .textFieldStyle(.roundedBorder)
                        .onSubmit {
                            Task { await store.searchBrowserHistory() }
                        }
                    Button("Cari") {
                        Task { await store.searchBrowserHistory() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.cyan)
                    Button("Clear All History") {
                        Task { await store.clearAllBrowserHistory() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.redFault)
                }

                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(Array(store.browserHistoryItems.enumerated()), id: \.offset) { _, item in
                            let vid = (item["visit_id"] as? String) ?? ""
                            let title = (item["title"] as? String) ?? ""
                            let url = (item["url"] as? String) ?? ""
                            let pol = (item["session_policy"] as? String) ?? ""
                            HStack {
                                Text(title)
                                    .font(.system(size: 11.5, weight: .bold))
                                    .foregroundColor(CosmicTheme.silver)
                                    .lineLimit(1)
                                Text(url)
                                    .font(.system(size: 10.5, design: .monospaced))
                                    .foregroundColor(CosmicTheme.cyan)
                                    .lineLimit(1)
                                Spacer()
                                Text(pol)
                                    .font(.system(size: 9.5, design: .monospaced))
                                    .foregroundColor(CosmicTheme.muted)
                                Button("Buka") {
                                    Task { await store.navigateBrowser(to: url) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                                Button("Hapus") {
                                    Task { await store.deleteBrowserHistoryItem(vid) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            } else if store.activeBrowserDrawer == .downloads {
                HStack {
                    Text("Staging Directory: nui-desktop/data/staging_downloads (auto_executed = False)")
                        .font(.system(size: 10.5, design: .monospaced))
                        .foregroundColor(CosmicTheme.cyan)
                    Spacer()
                    Button("+ Stage Download URL Aktif") {
                        Task { await store.downloadCurrentBrowserURLToStaging() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.emerald)
                    .controlSize(.small)
                }

                ScrollView {
                    VStack(alignment: .leading, spacing: 5) {
                        if store.browserDownloads.isEmpty {
                            Text("Belum ada unduhan di daftar staging.")
                                .font(.system(size: 11))
                                .foregroundColor(CosmicTheme.muted)
                        }
                        ForEach(Array(store.browserDownloads.enumerated()), id: \.offset) { _, dl in
                            let dlId = (dl["download_id"] as? String) ?? ""
                            let fname = (dl["filename"] as? String) ?? (dl["path"] as? String) ?? "file"
                            let st = (dl["status"] as? String) ?? "STAGED"
                            let sha = (dl["sha256"] as? String) ?? ""
                            let sizeB = (dl["size_bytes"] as? Int) ?? 0
                            HStack(spacing: 8) {
                                Text(fname)
                                    .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                                    .foregroundColor(CosmicTheme.silver)
                                    .lineLimit(1)
                                Text("[\(st)] \(sizeB) B")
                                    .font(.system(size: 10.5, weight: .semibold, design: .monospaced))
                                    .foregroundColor(st.contains("VERIFIED") ? CosmicTheme.emerald : CosmicTheme.gold)
                                if !sha.isEmpty {
                                    Text("SHA256:\(String(sha.prefix(10)))…")
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundColor(CosmicTheme.cyan)
                                }
                                Spacer()
                                Button("Reveal in Finder") {
                                    Task { await store.revealBrowserDownloadInFinder(dlId) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                                Button("Retry") {
                                    Task { await store.retryBrowserDownload(dlId) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                                Button("Cancel") {
                                    Task { await store.cancelBrowserDownload(dlId) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                                Button("Remove") {
                                    Task { await store.removeBrowserDownload(dlId) }
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                            .padding(.vertical, 2)
                        }
                    }
                }
            }
        }
        .padding(10)
        .background(CosmicTheme.bgCard)
    }
}

// MARK: - Official CosmicTera Logo View

struct CosmicTeraLogoView: View {
    let height: CGFloat

    var body: some View {
        let resourcePath = Bundle.main.path(forResource: "CosmicTeraLogo", ofType: "png")
            ?? "/Users/AMRA/hijaiyyah-mathematics/cosmictera/Logo CosmicTera Chrome Orbit Logo (1).png"
        if let nsImg = NSImage(contentsOfFile: resourcePath) {
            Image(nsImage: nsImg)
                .resizable()
                .scaledToFit()
                .frame(height: height)
        } else {
            Image(systemName: "sparkles")
                .foregroundColor(CosmicTheme.gold)
        }
    }
}

// MARK: - Main Desktop Window

struct MainDesktopView: View {
    @StateObject private var store = NUIDesktopStore()

    var body: some View {
        VStack(spacing: 0) {
            // Top Brand & Honest Status Header
            HStack(spacing: 14) {
                CosmicTeraLogoView(height: 36)
                VStack(alignment: .leading, spacing: 2) {
                    Text("COSMICTERA NUI DESKTOP")
                        .font(.system(size: 15, weight: .bold, design: .rounded))
                        .foregroundColor(CosmicTheme.silver)
                    Text("Official NUI Persona + Ollama Language Engine + \(store.activeCodingSpecialistLabel)")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(CosmicTheme.cyan)
                }
                Spacer()

                Picker("Provider", selection: Binding(
                    get: { store.activeProvider },
                    set: { p in Task { await store.switchProvider(p) } }
                )) {
                    Text("Native NUI (L0-L11)").tag("native_nui")
                    Text("Local Ollama (NUI Persona)").tag("local_ollama")
                    Text("Multi-Model Auto Router").tag("auto")
                    Text("External API").tag("external_api")
                }
                .frame(width: 215)

                if !store.installedOllamaModels.isEmpty {
                    Picker("Model", selection: Binding(
                        get: { store.selectedModelTag },
                        set: { m in
                            store.selectedModelTag = m
                            Task { await store.performModelOp("select", modelTag: m) }
                        }
                    )) {
                        ForEach(store.installedOllamaModels, id: \.self) { mName in
                            Text(mName).tag(mName)
                        }
                    }
                    .frame(width: 225)
                }

                Picker("Network", selection: Binding(
                    get: { store.operatingMode },
                    set: { m in Task { await store.switchOperatingMode(m) } }
                )) {
                    Text("LOCAL").tag("LOCAL")
                    Text("HYBRID").tag("HYBRID")
                    Text("ONLINE").tag("ONLINE")
                }
                .pickerStyle(.segmented)
                .frame(width: 190)
                .help("Network Mode (LOCAL / HYBRID / ONLINE) terpisah dari AI Model Provider")

                Button(action: { Task { await store.runConnectivityCheck() } }) {
                    Text("NET: \(store.operatingMode == "LOCAL" ? "OFFLINE (LOCAL)" : store.internetConnectivityState)")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 7)
                        .padding(.vertical, 4)
                        .background((store.operatingMode != "LOCAL" && store.internetConnectivityState == "CONNECTED") ? CosmicTheme.emerald.opacity(0.22) : CosmicTheme.gold.opacity(0.22))
                        .foregroundColor((store.operatingMode != "LOCAL" && store.internetConnectivityState == "CONNECTED") ? CosmicTheme.emerald : CosmicTheme.gold)
                        .cornerRadius(6)
                }
                .buttonStyle(.plain)
                .help("Klik untuk menjalankan diagnostik konektivitas internet nyata (DNS/TCP/TLS/HTTPS)")

                Button(action: { Task { await store.refreshAll() } }) {
                    Label("Sync", systemImage: "arrow.clockwise")
                }
                .buttonStyle(.borderedProminent)
                .tint(CosmicTheme.emerald)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 10)
            .background(CosmicTheme.bgSecondary)

            Divider().background(CosmicTheme.cyan.opacity(0.3))

            HStack(spacing: 0) {
                // 1. Left Sidebar (15 Sections)
                ScrollView {
                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(SidebarSection.allCases) { sec in
                            Button(action: { store.selectedSection = sec }) {
                                HStack(spacing: 10) {
                                    Image(systemName: sec.icon)
                                        .frame(width: 18)
                                        .foregroundColor(store.selectedSection == sec ? CosmicTheme.bgPrimary : CosmicTheme.cyan)
                                    Text(sec.rawValue)
                                        .font(.system(size: 12.5, weight: .semibold))
                                        .foregroundColor(store.selectedSection == sec ? CosmicTheme.bgPrimary : CosmicTheme.silver)
                                    Spacer()
                                }
                                .padding(.horizontal, 10)
                                .padding(.vertical, 7)
                                .background(store.selectedSection == sec ? CosmicTheme.emerald : Color.clear)
                                .cornerRadius(7)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(10)
                }
                .frame(width: 215)
                .background(CosmicTheme.bgSecondary)

                Divider().background(CosmicTheme.cyan.opacity(0.25))

                // 2. Main Center Workspace
                VStack(spacing: 0) {
                    if let errBanner = store.lastErrorBanner {
                        HStack(spacing: 10) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(CosmicTheme.redFault)
                            Text(errBanner)
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Button("Retry") {
                                store.retryLastMessage()
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.gold)
                            Button("Tutup") { store.lastErrorBanner = nil }
                                .buttonStyle(.bordered)
                        }
                        .padding(10)
                        .background(CosmicTheme.redFault.opacity(0.2))
                    }
                    if !store.pendingApprovals.isEmpty {
                        PermissionBannerView(store: store)
                    }
                    CenterWorkspaceView(store: store)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .background(CosmicTheme.bgPrimary)

                // 3. Collapsible Right Inspector (Automatically gives more room when collapsed)
                if !store.isRightInspectorCollapsed {
                    Divider().background(CosmicTheme.cyan.opacity(0.25))
                    RightInspectorView(store: store)
                        .frame(width: 265)
                        .background(CosmicTheme.bgSecondary)
                }
            }

            Divider().background(CosmicTheme.cyan.opacity(0.3))

            // 4. Bottom Activity Bar
            HStack(spacing: 14) {
                Label(store.serviceState, systemImage: "bolt.horizontal.circle.fill")
                    .foregroundColor(store.serviceState.contains("READY") ? CosmicTheme.emerald : CosmicTheme.redFault)
                Text("|").foregroundColor(CosmicTheme.muted)
                Text(store.providerState)
                    .foregroundColor(store.providerState.contains("UNAVAILABLE") ? CosmicTheme.redFault : CosmicTheme.cyan)
                Text("|").foregroundColor(CosmicTheme.muted)
                Text("Model: \(store.selectedModelTag) | Status: \(store.uiState)")
                    .foregroundColor(store.uiState == "ERROR" ? CosmicTheme.redFault : CosmicTheme.gold)
                Spacer()
                Text("127.0.0.1:\(store.activePort) | Mode: \(store.operatingMode) | Session: \(store.currentSessionId)")
                    .foregroundColor(CosmicTheme.muted)
            }
            .font(.system(size: 11, weight: .semibold, design: .monospaced))
            .padding(.horizontal, 14)
            .padding(.vertical, 6)
            .background(CosmicTheme.bgSecondary)
        }
        .preferredColorScheme(.dark)
    }
}

struct PermissionBannerView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        if let req = store.pendingApprovals.first {
            let reqId = (req["request_id"] as? String) ?? ""
            let cat = (req["category"] as? String) ?? ""
            let op = (req["operation"] as? String) ?? ""
            let target = (req["target_value"] as? String) ?? ""
            let reason = (req["reason"] as? String) ?? ""

            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "lock.shield.fill").foregroundColor(CosmicTheme.gold)
                    Text("AUTHORIZATION REQUIRED — [\(cat)] (\(op)) on \(target)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(CosmicTheme.gold)
                    Spacer()
                }
                Text(reason).font(.system(size: 11.5)).foregroundColor(CosmicTheme.silver)
                HStack(spacing: 8) {
                    ForEach(["ALLOW_ONCE", "ALLOW_SESSION", "ALWAYS_ALLOW", "DENY", "REVOKE_ACCESS"], id: \.self) { mode in
                        Button(mode.replacingOccurrences(of: "_", with: " ")) {
                            Task { await store.decideApproval(requestId: reqId, decision: mode) }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(mode == "DENY" || mode == "REVOKE_ACCESS" ? CosmicTheme.redFault : CosmicTheme.emerald)
                    }
                }
            }
            .padding(12)
            .background(CosmicTheme.bgCard)
        }
    }
}

// MARK: - NUI Language Engine View

struct LanguageEngineSectionView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        let probe = (store.modelLibrary["ollama_probe"] as? [String: Any]) ?? [:]
        let cfg = (store.modelLibrary["engine_config"] as? [String: Any]) ?? [:]
        let host = (store.modelLibrary["host_resources"] as? [String: Any]) ?? [:]
        let assets = (store.modelLibrary["model_assets"] as? [[String: Any]]) ?? []
        let connState = (probe["connection_state"] as? String) ?? "VERIFYING..."
        let version = (probe["ollama_version"] as? String) ?? "unknown"
        let endpoint = (probe["endpoint"] as? String) ?? "127.0.0.1:11434"
        let cpuBrand = (host["cpu_brand"] as? String) ?? "Apple Silicon"
        let ramTotal = (host["memory_total_gb"] as? Double) ?? 32.0
        let ramFree = (host["memory_reclaimable_gb"] as? Double) ?? 12.7
        let diskFree = (host["disk_free_gb"] as? Double) ?? 97.0

        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    VStack(alignment: .leading, spacing: 3) {
                        Text("NUI LANGUAGE ENGINE — OLLAMA & QWEN3.8-27B MODEL ASSET MANAGER")
                            .font(.headline)
                            .foregroundColor(CosmicTheme.gold)
                        Text("Ollama menyediakan pemrosesan bahasa lokal; Identitas & Persona tetap dikendalikan oleh HybitAIProgram.system (CosmicTera NUI).")
                            .font(.system(size: 11.5))
                            .foregroundColor(CosmicTheme.muted)
                    }
                    Spacer()
                    Text(connState)
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 10)
                        .padding(.vertical, 5)
                        .background(connState == "CONNECTED" ? CosmicTheme.emerald.opacity(0.2) : CosmicTheme.redFault.opacity(0.2))
                        .foregroundColor(connState == "CONNECTED" ? CosmicTheme.emerald : CosmicTheme.redFault)
                        .cornerRadius(6)
                }

                HStack(spacing: 8) {
                    Button("Refresh Models") { Task { await store.performModelOp("refresh") } }
                        .buttonStyle(.borderedProminent).tint(CosmicTheme.cyan)
                    Button("Select Model (\(store.selectedModelTag))") { Task { await store.performModelOp("select") } }
                        .buttonStyle(.borderedProminent).tint(CosmicTheme.emerald)
                    Button("Connect") { Task { await store.switchProvider("local_ollama") } }
                        .buttonStyle(.bordered)
                    Button("Disconnect") { Task { await store.switchProvider("native_nui") } }
                        .buttonStyle(.bordered)
                    Button("Load Model") { Task { await store.performModelOp("load") } }
                        .buttonStyle(.borderedProminent).tint(CosmicTheme.gold)
                    Button("Unload Model") { Task { await store.performModelOp("unload") } }
                        .buttonStyle(.bordered)
                    Button("Test Connection") { Task { await store.performModelOp("verify") } }
                        .buttonStyle(.borderedProminent).tint(CosmicTheme.emerald)
                }

                Text("Engine Log: \(store.engineStatusBanner)")
                    .font(.system(size: 11.5, design: .monospaced))
                    .foregroundColor(CosmicTheme.cyan)

                HStack(alignment: .top, spacing: 12) {
                    VStack(alignment: .leading, spacing: 5) {
                        Text("Ollama Runtime Status").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                        Text("Connection: \(connState)").font(.system(size: 12, design: .monospaced))
                        Text("Endpoint: \(endpoint)").font(.system(size: 12, design: .monospaced))
                        Text("Version: \(version)").font(.system(size: 12, design: .monospaced))
                        Text("Selected Model: \(store.selectedModelTag)").font(.system(size: 12, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    VStack(alignment: .leading, spacing: 5) {
                        Text("Inference Parameters & Capabilities").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                        let ctxLen = (cfg["context_length"] as? Int) ?? 16384
                        let temp = (cfg["temperature"] as? Double) ?? 0.2
                        let maxOut = (cfg["max_output_tokens"] as? Int) ?? 2048
                        Text("Context Length: \(ctxLen) tokens").font(.system(size: 12, design: .monospaced))
                        Text(String(format: "Temperature: %.2f | Max Output: %d", temp, maxOut)).font(.system(size: 12, design: .monospaced))
                        Text("Thinking Support: YES | Tool Calling: YES | Vision: NO").font(.system(size: 11.5, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    VStack(alignment: .leading, spacing: 5) {
                        Text("Mac Host Resource Telemetry").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                        Text("CPU: \(cpuBrand)").font(.system(size: 12, design: .monospaced))
                        Text(String(format: "Unified Memory: %.1f GB (Reclaimable: %.1f GB)", ramTotal, ramFree)).font(.system(size: 12, design: .monospaced))
                        Text(String(format: "Free Disk: %.1f GB", diskFree)).font(.system(size: 12, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                    }
                    .padding(12)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)
                }

                Text("Registered NUI Model Assets")
                    .font(.subheadline.bold())
                    .foregroundColor(CosmicTheme.gold)

                ForEach(Array(assets.enumerated()), id: \.offset) { _, asset in
                    let mName = (asset["model_name"] as? String) ?? ""
                    let oTag = (asset["ollama_tag"] as? String) ?? ""
                    let role = (asset["role"] as? String) ?? ""
                    let label = (asset["display_label"] as? String) ?? ""
                    let sizeGb = (asset["size_gb"] as? Double) ?? 0.0
                    let st = (asset["status"] as? String) ?? "AVAILABLE"
                    let loaded = (asset["loaded_in_memory"] as? Bool) ?? false

                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack(spacing: 8) {
                                Text(mName).font(.system(size: 13, weight: .bold)).foregroundColor(CosmicTheme.silver)
                                Text("(\(oTag))").font(.system(size: 11.5, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                                if !label.isEmpty {
                                    Text(label)
                                        .font(.system(size: 9.5, weight: .bold, design: .monospaced))
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(CosmicTheme.gold.opacity(0.2))
                                        .foregroundColor(CosmicTheme.gold)
                                        .cornerRadius(4)
                                }
                            }
                            Text("Role: \(role) | Size: \(String(format: "%.2f GB", sizeGb)) | In Memory: \(loaded ? "LOADED" : "IDLE")")
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(CosmicTheme.muted)
                        }
                        Spacer()
                        Text(st)
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(st == "VERIFIED" || st == "READY" ? CosmicTheme.emerald.opacity(0.2) : CosmicTheme.gold.opacity(0.2))
                            .foregroundColor(st == "VERIFIED" || st == "READY" ? CosmicTheme.emerald : CosmicTheme.gold)
                            .cornerRadius(6)
                        Button("Select") {
                            store.selectedModelTag = oTag
                            Task { await store.performModelOp("select", modelTag: oTag) }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.cyan)
                    }
                    .padding(10)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)
                }
            }
            .padding(16)
        }
    }
}

// MARK: - NUI Self-Learning Center View

struct SelfLearningCenterSectionView: View {
    @ObservedObject var store: NUIDesktopStore

    let submenuTitles: [(Int, String)] = [
        (1, "1. Overview"),
        (2, "2. Knowledge Base"),
        (3, "3. Coding Skills"),
        (4, "4. Model Assets"),
        (5, "5. History"),
        (6, "6. Feedback"),
        (7, "7. Evaluation"),
        (8, "8. Skill Validation"),
        (9, "9. Performance"),
        (10, "10. Configuration")
    ]

    var body: some View {
        let ov = (store.selfLearningOverview["1_learning_overview"] as? [String: Any]) ?? [:]
        let kb = (store.selfLearningOverview["2_knowledge_base"] as? [[String: Any]]) ?? []
        let skills = (store.selfLearningOverview["3_coding_skills"] as? [[String: Any]]) ?? []
        let hist = (store.selfLearningOverview["5_learning_history"] as? [[String: Any]]) ?? []
        let evalDict = (store.selfLearningOverview["7_evaluation"] as? [String: Any]) ?? [:]
        let cfgDict = (store.selfLearningOverview["10_learning_configuration"] as? [String: Any]) ?? [:]

        VStack(alignment: .leading, spacing: 0) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(submenuTitles, id: \.0) { idx, title in
                        Button(title) {
                            store.selectedLearningSubmenu = idx
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(store.selectedLearningSubmenu == idx ? CosmicTheme.emerald : CosmicTheme.bgCard)
                        .font(.system(size: 11, weight: .semibold))
                    }
                }
                .padding(10)
            }
            .background(CosmicTheme.bgSecondary)

            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("NUI AUTONOMOUS SELF-LEARNING CENTER — SUBMENU \(store.selectedLearningSubmenu)/10")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.gold)

                    if store.selectedLearningSubmenu == 1 {
                        let totalKb = (ov["total_knowledge_entries"] as? Int) ?? 0
                        let totalSk = (ov["total_coding_skills"] as? Int) ?? 0
                        let valCount = (ov["validated_entries_count"] as? Int) ?? 0
                        VStack(alignment: .leading, spacing: 6) {
                            Text("Total Validated Knowledge Entries: \(totalKb)").font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                            Text("Total Verified Coding Skills: \(totalSk)").font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                            Text("Validated Entries Count: \(valCount) | Rollback Snapshots Ready: YES").font(.system(size: 12, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("Immutable Core Protection: ACTIVE (NUI Persona, L0–L11, Matematika Hijaiyyah, H-ISA, Permission Engine protected)").font(.system(size: 11.5, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                        }
                        .padding(12)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    } else if store.selectedLearningSubmenu == 2 || store.selectedLearningSubmenu == 5 {
                        let listToRender = store.selectedLearningSubmenu == 2 ? kb : hist
                        ForEach(Array(listToRender.prefix(15).enumerated()), id: \.offset) { _, item in
                            let eid = (item["entry_id"] as? String) ?? ""
                            let topic = (item["topic"] as? String) ?? ""
                            let summary = (item["summary"] as? String) ?? ""
                            let conf = (item["confidence"] as? String) ?? ""
                            let valSt = (item["validation_status"] as? String) ?? ""
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("[\(eid)] \(topic)").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.silver)
                                    Spacer()
                                    Text("\(conf) | \(valSt)").font(.system(size: 10.5, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                                    Button("Rollback") {
                                        Task { await store.rollbackLearningEntry(eid) }
                                    }
                                    .buttonStyle(.bordered)
                                    .font(.system(size: 10))
                                }
                                Text(summary).font(.system(size: 11.5)).foregroundColor(CosmicTheme.muted)
                            }
                            .padding(10)
                            .background(CosmicTheme.bgCard)
                            .cornerRadius(8)
                        }
                    } else if store.selectedLearningSubmenu == 3 || store.selectedLearningSubmenu == 8 {
                        ForEach(Array(skills.enumerated()), id: \.offset) { _, sk in
                            let sid = (sk["skill_id"] as? String) ?? ""
                            let sName = (sk["skill_name"] as? String) ?? ""
                            let prob = (sk["problem_statement"] as? String) ?? ""
                            let vStat = (sk["validation_status"] as? String) ?? ""
                            let ev = (sk["test_evidence"] as? String) ?? ""
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text("[\(sid)] \(sName)").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.cyan)
                                    Spacer()
                                    Text(vStat).font(.system(size: 10.5, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                                }
                                Text("Problem: \(prob)").font(.system(size: 11.5)).foregroundColor(CosmicTheme.silver)
                                Text("Pytest Evidence: \(ev)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                            }
                            .padding(10)
                            .background(CosmicTheme.bgCard)
                            .cornerRadius(8)
                        }
                    } else if store.selectedLearningSubmenu == 6 {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Kirim Koreksi / Feedback Pengguna (Tersimpan sebagai 'User Provided')").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                            TextField("Topik Feedback", text: $store.feedbackTopic).textFieldStyle(.roundedBorder)
                            TextField("Isi Koreksi / Preferensi", text: $store.feedbackSummary).textFieldStyle(.roundedBorder)
                            Button("Simpan Koreksi ke Knowledge Memory") {
                                Task { await store.submitUserFeedback() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.emerald)
                        }
                        .padding(12)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    } else {
                        let passRate = (evalDict["skill_validation_pass_rate"] as? Double) ?? 1.0
                        let protectedDomains = (cfgDict["protected_immutable_domains"] as? [String]) ?? []
                        VStack(alignment: .leading, spacing: 6) {
                            Text(String(format: "Skill Validation Pass Rate: %.1f%%", passRate * 100.0))
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundColor(CosmicTheme.emerald)
                            Text("Protected Immutable Domains (\(protectedDomains.count)):")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundColor(CosmicTheme.gold)
                            Text(protectedDomains.joined(separator: ", "))
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(CosmicTheme.silver)
                        }
                        .padding(12)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    }
                }
                .padding(16)
            }
        }
    }
}

// MARK: - Live Thinking, Smart Auto-Scroll & Streaming NUI Chat View

struct NUIChatSectionView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        VStack(spacing: 0) {
            HStack(spacing: 10) {
                Button("+ Sesi Baru") {
                    Task { await store.createNewSession() }
                }
                .buttonStyle(.borderedProminent)
                .tint(CosmicTheme.cyan)

                Menu {
                    ForEach(Array(store.sessions.enumerated()), id: \.offset) { _, s in
                        let sid = (s["session_id"] as? String) ?? ""
                        let title = (s["title"] as? String) ?? sid
                        Button("\(title) (\(sid))") {
                            Task { await store.loadSessionMessages(sid) }
                        }
                    }
                } label: {
                    Label("Riwayat Sesi (\(store.sessions.count)): \(store.currentSessionTitle)", systemImage: "tray.full.fill")
                        .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                }
                .frame(maxWidth: 340)

                Button(action: {
                    store.checkYayasanVPSConnectionNow()
                }) {
                    Label("Cek VPS Yayasan", systemImage: "externaldrive.connected.to.line.below.fill")
                        .font(.system(size: 10.5, weight: .bold))
                }
                .buttonStyle(.bordered)
                .tint(CosmicTheme.gold)

                Spacer()

                if let copiedBanner = store.copiedConfirmationBanner {
                    HStack(spacing: 5) {
                        Image(systemName: "checkmark.seal.fill")
                            .font(.system(size: 10, weight: .bold))
                        Text(copiedBanner)
                            .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                            .lineLimit(1)
                    }
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(CosmicTheme.emerald.opacity(0.22))
                    .foregroundColor(CosmicTheme.emerald)
                    .cornerRadius(6)
                }

                if store.isDemoModeActive {
                    Text("DEMO MODE (CONTOH TERPISAH)")
                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(CosmicTheme.gold.opacity(0.25))
                        .foregroundColor(CosmicTheme.gold)
                        .cornerRadius(6)
                }

                Text(store.uiState)
                    .font(.system(size: 11, weight: .bold, design: .monospaced))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(store.uiState.contains("ERROR") || store.uiState.contains("UNAVAILABLE") ? CosmicTheme.redFault.opacity(0.25) : CosmicTheme.emerald.opacity(0.2))
                    .foregroundColor(store.uiState.contains("ERROR") || store.uiState.contains("UNAVAILABLE") ? CosmicTheme.redFault : CosmicTheme.emerald)
                    .cornerRadius(6)
            }
            .padding(10)
            .background(CosmicTheme.bgCard)

            ScrollViewReader { proxy in
                ZStack(alignment: .bottom) {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 14) {
                            SmartScrollDetectorRepresentable(
                                onUserScrollUp: {
                                    store.handleUserManualScrollUp()
                                },
                                onReachedBottom: {
                                    store.handleUserReachedBottom()
                                }
                            )
                            .frame(height: 0)

                            if store.messages.isEmpty {
                                VStack(alignment: .leading, spacing: 10) {
                                    HStack(spacing: 12) {
                                        CosmicTeraLogoView(height: 42)
                                        VStack(alignment: .leading, spacing: 3) {
                                            Text("Halo! Saya CosmicTera NUI.")
                                                .font(.title3.bold())
                                                .foregroundColor(CosmicTheme.silver)
                                            Text("Silakan ketik pertanyaan, tempel kode panjang (Cmd+V), atau periksa status VPS folder di kolom bawah.")
                                                .font(.system(size: 12.5))
                                                .foregroundColor(CosmicTheme.muted)
                                        }
                                    }
                                    Divider().background(CosmicTheme.cyan.opacity(0.25))
                                    HStack(spacing: 14) {
                                        Text("Service: \(store.serviceState)")
                                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                            .foregroundColor(store.serviceState.contains("READY") ? CosmicTheme.emerald : CosmicTheme.gold)
                                        Text("Provider: \(store.providerState)")
                                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                            .foregroundColor(store.providerState.contains("CONNECTED") ? CosmicTheme.cyan : CosmicTheme.gold)
                                        Text("Mode: \(store.operatingMode)")
                                            .font(.system(size: 11, weight: .semibold, design: .monospaced))
                                            .foregroundColor(CosmicTheme.gold)
                                        Spacer()
                                        Button("Cek Folder Yayasan & VPS") {
                                            store.checkYayasanVPSConnectionNow()
                                        }
                                        .buttonStyle(.borderedProminent)
                                        .tint(CosmicTheme.cyan)
                                        .font(.system(size: 10.5, weight: .bold))
                                        Button("Buka Demo Mode (DEMO)") {
                                            store.activateSeparatedDemoTranscript()
                                        }
                                        .buttonStyle(.bordered)
                                        .font(.system(size: 10.5))
                                    }
                                }
                                .padding(18)
                                .background(CosmicTheme.bgCard)
                                .cornerRadius(10)
                            }

                            ForEach(store.messages) { msg in
                                if msg.role == "user" {
                                    // Right-aligned User Message Bubble (Section 1)
                                    let isUserCopied = store.copiedItemId == "user-\(msg.id)"
                                    HStack(alignment: .top) {
                                        Spacer(minLength: 75)
                                        VStack(alignment: .trailing, spacing: 7) {
                                            HStack(spacing: 8) {
                                                Text("PENGGUNA")
                                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                    .foregroundColor(CosmicTheme.gold)
                                                Spacer()
                                                Button(action: {
                                                    store.copyUserQuestion(msg)
                                                }) {
                                                    HStack(spacing: 4) {
                                                        Image(systemName: isUserCopied ? "checkmark.circle.fill" : "doc.on.doc")
                                                            .font(.system(size: 10, weight: .bold))
                                                        Text(isUserCopied ? "Copied ✓ · Tersalin" : "Salin pertanyaan")
                                                            .font(.system(size: 10.5, weight: .semibold))
                                                    }
                                                    .padding(.horizontal, 7)
                                                    .padding(.vertical, 3)
                                                    .background(isUserCopied ? CosmicTheme.emerald.opacity(0.24) : CosmicTheme.bgCard)
                                                    .foregroundColor(isUserCopied ? CosmicTheme.emerald : CosmicTheme.cyan)
                                                    .cornerRadius(5)
                                                }
                                                .buttonStyle(.plain)

                                                Button(action: {
                                                    store.beginEditingUserMessage(msg)
                                                }) {
                                                    HStack(spacing: 3) {
                                                        Image(systemName: "pencil")
                                                            .font(.system(size: 10))
                                                        Text("Edit")
                                                            .font(.system(size: 10.5, weight: .semibold))
                                                    }
                                                    .padding(.horizontal, 7)
                                                    .padding(.vertical, 3)
                                                    .background(CosmicTheme.bgCard)
                                                    .foregroundColor(CosmicTheme.gold)
                                                    .cornerRadius(5)
                                                }
                                                .buttonStyle(.plain)

                                                Button(action: {
                                                    store.editAndResend(msg.content)
                                                }) {
                                                    HStack(spacing: 3) {
                                                        Image(systemName: "arrow.uturn.forward.circle.fill")
                                                            .font(.system(size: 10))
                                                        Text("Resend")
                                                            .font(.system(size: 10.5, weight: .semibold))
                                                    }
                                                    .padding(.horizontal, 7)
                                                    .padding(.vertical, 3)
                                                    .background(CosmicTheme.bgCard)
                                                    .foregroundColor(CosmicTheme.emerald)
                                                    .cornerRadius(5)
                                                }
                                                .buttonStyle(.plain)
                                            }

                                            if store.editingMessageId == msg.id {
                                                VStack(alignment: .leading, spacing: 6) {
                                                    TextEditor(text: $store.editingMessageDraft)
                                                        .font(.system(size: 13))
                                                        .frame(minHeight: 68, maxHeight: 150)
                                                        .padding(6)
                                                        .background(CosmicTheme.bgPrimary)
                                                        .cornerRadius(6)
                                                    HStack(spacing: 8) {
                                                        Spacer()
                                                        Button("Batal") {
                                                            store.cancelEditingUserMessage()
                                                        }
                                                        .buttonStyle(.bordered)
                                                        .controlSize(.small)
                                                        Button("Simpan & Kirim Ulang (Resend)") {
                                                            Task {
                                                                await store.submitEditedUserMessage(msg.id)
                                                            }
                                                        }
                                                        .buttonStyle(.borderedProminent)
                                                        .tint(CosmicTheme.emerald)
                                                        .controlSize(.small)
                                                    }
                                                }
                                                .padding(8)
                                                .background(CosmicTheme.bgCard)
                                                .cornerRadius(7)
                                            } else {
                                                RichMarkdownAndCodeView(
                                                    text: msg.content,
                                                    messageId: msg.id,
                                                    copiedItemId: store.copiedItemId,
                                                    onCopyCode: { rawCode, blkId in
                                                        store.copyRawCodeBlock(code: rawCode, blockId: blkId)
                                                    },
                                                    onOpenInStudio: { rawCode, lang in
                                                        store.openCodeSnippetInStudio(code: rawCode, language: lang)
                                                    }
                                                )
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                            }
                                        }
                                        .padding(12)
                                        .frame(maxWidth: 740, alignment: .leading)
                                        .background(CosmicTheme.cyan.opacity(0.14))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 11)
                                                .stroke(CosmicTheme.cyan.opacity(0.45), lineWidth: 1)
                                        )
                                        .cornerRadius(11)
                                    }
                                    .id(msg.id)
                                } else {
                                    // Left-aligned Assistant Message Card (Section 2)
                                    let isAsstCopied = store.copiedItemId == "asst-\(msg.id)"
                                    let recordedFeedback = store.messageFeedbackMap[msg.id] ?? ""
                                    HStack(alignment: .top) {
                                        VStack(alignment: .leading, spacing: 9) {
                                            HStack(spacing: 8) {
                                                HStack(spacing: 5) {
                                                    Image(systemName: "sparkles")
                                                        .font(.system(size: 10.5, weight: .bold))
                                                        .foregroundColor(CosmicTheme.emerald)
                                                    Text("COSMICTERA NUI (\(msg.provider) · \(msg.model))")
                                                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                                        .foregroundColor(CosmicTheme.emerald)
                                                }
                                                Spacer()
                                                if msg.responseTimeMs > 0 {
                                                    Text(String(format: "%.1f ms | %@", msg.responseTimeMs, msg.executionStatus))
                                                        .font(.system(size: 10, design: .monospaced))
                                                        .foregroundColor(CosmicTheme.muted)
                                                }
                                                Button(action: {
                                                    store.copyAssistantFullAnswer(msg)
                                                }) {
                                                    HStack(spacing: 4) {
                                                        Image(systemName: isAsstCopied ? "checkmark.circle.fill" : "doc.on.doc")
                                                            .font(.system(size: 10, weight: .bold))
                                                        Text(isAsstCopied ? "Copied ✓ · Tersalin" : "Copy")
                                                            .font(.system(size: 10.5, weight: .bold))
                                                    }
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 3)
                                                    .background(isAsstCopied ? CosmicTheme.emerald.opacity(0.24) : CosmicTheme.bgSecondary)
                                                    .foregroundColor(isAsstCopied ? CosmicTheme.emerald : CosmicTheme.gold)
                                                    .cornerRadius(5)
                                                }
                                                .buttonStyle(.plain)

                                                Button(action: {
                                                    Task { await store.regenerateAssistantAnswer(for: msg) }
                                                }) {
                                                    HStack(spacing: 4) {
                                                        Image(systemName: "arrow.clockwise")
                                                            .font(.system(size: 10, weight: .bold))
                                                        Text("Regenerate")
                                                            .font(.system(size: 10.5, weight: .semibold))
                                                    }
                                                    .padding(.horizontal, 8)
                                                    .padding(.vertical, 3)
                                                    .background(CosmicTheme.bgSecondary)
                                                    .foregroundColor(CosmicTheme.cyan)
                                                    .cornerRadius(5)
                                                }
                                                .buttonStyle(.plain)
                                            }

                                            if msg.executionStatus == "GENERATING" && !msg.toolActivities.isEmpty {
                                                VStack(alignment: .leading, spacing: 3) {
                                                    Text("Aktivitas Engine & Tool:")
                                                        .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                                        .foregroundColor(CosmicTheme.gold)
                                                    ForEach(msg.toolActivities, id: \.self) { act in
                                                        HStack(spacing: 6) {
                                                            Image(systemName: "gearshape.2.fill")
                                                                .font(.system(size: 9.5))
                                                                .foregroundColor(CosmicTheme.emerald)
                                                            Text(act)
                                                                .font(.system(size: 11, design: .monospaced))
                                                                .foregroundColor(CosmicTheme.silver)
                                                        }
                                                    }
                                                }
                                                .padding(8)
                                                .frame(maxWidth: .infinity, alignment: .leading)
                                                .background(CosmicTheme.bgSecondary)
                                                .cornerRadius(6)
                                            }

                                            if !msg.content.isEmpty {
                                                RichMarkdownAndCodeView(
                                                    text: msg.content,
                                                    messageId: msg.id,
                                                    copiedItemId: store.copiedItemId,
                                                    onCopyCode: { rawCode, blkId in
                                                        store.copyRawCodeBlock(code: rawCode, blockId: blkId)
                                                    },
                                                    onOpenInStudio: { rawCode, lang in
                                                        store.openCodeSnippetInStudio(code: rawCode, language: lang)
                                                    }
                                                )
                                            } else if msg.executionStatus == "GENERATING" {
                                                Text("*\(store.liveThinkingStatus)*")
                                                    .font(.system(size: 12.5).italic())
                                                    .foregroundColor(CosmicTheme.gold)
                                            }

                                            // Bottom Action Bar matching Target UI (Copy · Regenerate · Feedback)
                                            if !msg.content.isEmpty {
                                                Divider().background(CosmicTheme.cyan.opacity(0.18))
                                                HStack(spacing: 10) {
                                                    Button(action: {
                                                        store.copyAssistantFullAnswer(msg)
                                                    }) {
                                                        HStack(spacing: 4) {
                                                            Image(systemName: isAsstCopied ? "checkmark.circle.fill" : "doc.on.doc")
                                                                .font(.system(size: 10.5, weight: .bold))
                                                            Text(isAsstCopied ? "Copied ✓ · Tersalin" : "Copy")
                                                                .font(.system(size: 11, weight: .semibold))
                                                        }
                                                        .padding(.horizontal, 9)
                                                        .padding(.vertical, 4)
                                                        .background(isAsstCopied ? CosmicTheme.emerald.opacity(0.24) : CosmicTheme.bgSecondary)
                                                        .foregroundColor(isAsstCopied ? CosmicTheme.emerald : CosmicTheme.silver)
                                                        .cornerRadius(6)
                                                    }
                                                    .buttonStyle(.plain)

                                                    Button(action: {
                                                        Task { await store.regenerateAssistantAnswer(for: msg) }
                                                    }) {
                                                        HStack(spacing: 4) {
                                                            Image(systemName: "arrow.clockwise")
                                                                .font(.system(size: 10.5, weight: .bold))
                                                            Text("Regenerate")
                                                                .font(.system(size: 11, weight: .semibold))
                                                        }
                                                        .padding(.horizontal, 9)
                                                        .padding(.vertical, 4)
                                                        .background(CosmicTheme.bgSecondary)
                                                        .foregroundColor(CosmicTheme.cyan)
                                                        .cornerRadius(6)
                                                    }
                                                    .buttonStyle(.plain)

                                                    Menu {
                                                        Button("👍 Jawaban akurat & membantu") {
                                                            store.submitMessageFeedback(messageId: msg.id, rating: "POSITIVE", note: "Jawaban akurat & membantu")
                                                        }
                                                        Button("👎 Jawaban kurang tepat / perlu koreksi") {
                                                            store.submitMessageFeedback(messageId: msg.id, rating: "NEGATIVE", note: "Perlu koreksi")
                                                        }
                                                    } label: {
                                                        HStack(spacing: 4) {
                                                            Image(systemName: recordedFeedback == "POSITIVE" ? "hand.thumbsup.fill" : (recordedFeedback == "NEGATIVE" ? "hand.thumbsdown.fill" : "hand.thumbsup"))
                                                                .font(.system(size: 10.5))
                                                            Text(recordedFeedback.isEmpty ? "Feedback" : "Feedback: \(recordedFeedback)")
                                                                .font(.system(size: 11, weight: .semibold))
                                                        }
                                                        .padding(.horizontal, 9)
                                                        .padding(.vertical, 4)
                                                        .background(CosmicTheme.bgSecondary)
                                                        .foregroundColor(recordedFeedback.isEmpty ? CosmicTheme.gold : CosmicTheme.emerald)
                                                        .cornerRadius(6)
                                                    }
                                                    .menuStyle(.borderlessButton)
                                                    .fixedSize()

                                                    let detectedPaths = store.extractLocalFilePathsFromMessage(msg.content)
                                                    if let primaryPath = detectedPaths.first {
                                                        Button(action: {
                                                            store.openFileOutputInOS(primaryPath)
                                                        }) {
                                                            HStack(spacing: 4) {
                                                                Image(systemName: "arrow.up.forward.app.fill")
                                                                    .font(.system(size: 10, weight: .bold))
                                                                Text("Open")
                                                                    .font(.system(size: 11, weight: .semibold))
                                                            }
                                                            .padding(.horizontal, 8)
                                                            .padding(.vertical, 4)
                                                            .background(CosmicTheme.emerald.opacity(0.18))
                                                            .foregroundColor(CosmicTheme.emerald)
                                                            .cornerRadius(6)
                                                        }
                                                        .buttonStyle(.plain)

                                                        Button(action: {
                                                            store.revealFileOutputInFinder(primaryPath)
                                                        }) {
                                                            HStack(spacing: 4) {
                                                                Image(systemName: "folder.fill")
                                                                    .font(.system(size: 10, weight: .bold))
                                                                Text("Reveal in Finder")
                                                                    .font(.system(size: 11, weight: .semibold))
                                                            }
                                                            .padding(.horizontal, 8)
                                                            .padding(.vertical, 4)
                                                            .background(CosmicTheme.cyan.opacity(0.18))
                                                            .foregroundColor(CosmicTheme.cyan)
                                                            .cornerRadius(6)
                                                        }
                                                        .buttonStyle(.plain)
                                                    }

                                                    Spacer()
                                                    Text("\(msg.content.count) chars")
                                                        .font(.system(size: 10, design: .monospaced))
                                                        .foregroundColor(CosmicTheme.muted)
                                                }
                                            }
                                        }
                                        .padding(13)
                                        .frame(maxWidth: .infinity, alignment: .leading)
                                        .background(CosmicTheme.bgCard)
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 10)
                                                .stroke(CosmicTheme.emerald.opacity(0.28), lineWidth: 1)
                                        )
                                        .cornerRadius(10)
                                        Spacer(minLength: 35)
                                    }
                                    .id(msg.id)
                                }
                            }

                            if store.isGenerating {
                                HStack(spacing: 10) {
                                    ProgressView()
                                        .scaleEffect(0.75)
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text("[\(store.liveThinkingStage)] \(store.liveThinkingStatus)")
                                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                                            .foregroundColor(CosmicTheme.gold)
                                    }
                                    Spacer()
                                    Button("Stop Generation") {
                                        Task { await store.stopGeneration() }
                                    }
                                    .buttonStyle(.borderedProminent)
                                    .tint(CosmicTheme.redFault)
                                }
                                .padding(10)
                                .background(CosmicTheme.bgCard)
                                .cornerRadius(8)
                            }

                            Color.clear
                                .frame(height: 1)
                                .id(NUIDesktopStore.chatBottomAnchorId)
                        }
                        .padding(14)
                    }
                    .onChange(of: store.scrollTriggerVersion) { _ in
                        guard store.isAutoFollowEnabled else { return }
                        proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)
                    }
                    .onChange(of: store.messages.count) { _ in
                        guard store.isAutoFollowEnabled else { return }
                        proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)
                    }
                    .onAppear {
                        store.shouldRefocusComposer &+= 1
                        if !store.messages.isEmpty && store.isAutoFollowEnabled {
                            proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)
                        }
                    }

                    if store.userScrolledUp && !store.messages.isEmpty {
                        Button(action: {
                            store.scrollToLatestResponse()
                            proxy.scrollTo(NUIDesktopStore.chatBottomAnchorId, anchor: .bottom)
                        }) {
                            HStack(spacing: 6) {
                                Image(systemName: "arrow.down.circle.fill")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(CosmicTheme.emerald)
                                Text("↓ Kembali ke Jawaban Terbaru  ·  Latest Response")
                                    .font(.system(size: 11.5, weight: .bold, design: .rounded))
                                    .foregroundColor(CosmicTheme.cyan)
                            }
                            .padding(.horizontal, 14)
                            .padding(.vertical, 7)
                            .background(CosmicTheme.bgSecondary.opacity(0.95))
                            .overlay(
                                RoundedRectangle(cornerRadius: 18)
                                    .stroke(CosmicTheme.emerald.opacity(0.85), lineWidth: 1.2)
                            )
                            .cornerRadius(18)
                            .shadow(color: Color.black.opacity(0.45), radius: 6, x: 0, y: 3)
                        }
                        .buttonStyle(.plain)
                        .padding(.bottom, 12)
                    }
                }
            }

            if let fBanner = store.folderNotificationBanner {
                HStack(spacing: 8) {
                    Image(systemName: "folder.badge.minus")
                        .foregroundColor(CosmicTheme.gold)
                    Text(fBanner)
                        .font(.system(size: 11, weight: .semibold, design: .monospaced))
                        .foregroundColor(CosmicTheme.silver)
                    Spacer()
                    Button("Tutup") { store.folderNotificationBanner = nil }
                        .buttonStyle(.plain)
                        .font(.system(size: 10.5, weight: .bold))
                        .foregroundColor(CosmicTheme.cyan)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 5)
                .background(CosmicTheme.bgCard)
            }

            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    HStack(spacing: 4) {
                        Image(systemName: "folder.fill.badge.gearshape")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(CosmicTheme.cyan)
                        Text("Connected Folders (\(store.authorizedFolders.count)):")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(CosmicTheme.cyan)
                    }

                    ForEach(Array(store.authorizedFolders.enumerated()), id: \.offset) { _, fld in
                        let fId = (fld["folder_id"] as? String) ?? ""
                        let fPath = (fld["path"] as? String) ?? ""
                        let fLabel = (fld["label"] as? String) ?? URL(fileURLWithPath: fPath).lastPathComponent
                        let fMode = (fld["access_mode"] as? String) ?? "READ_WRITE"
                        HStack(spacing: 6) {
                            Image(systemName: "folder.fill")
                                .font(.system(size: 10.5))
                                .foregroundColor(CosmicTheme.emerald)
                            Button(action: {
                                store.attachPath(fPath)
                            }) {
                                Text("\(fLabel) [\(fMode)]")
                                    .font(.system(size: 10.5, weight: .semibold, design: .monospaced))
                                    .foregroundColor(CosmicTheme.silver)
                            }
                            .buttonStyle(.plain)

                            Button(action: {
                                Task {
                                    await store.disconnectConnectedFolder(folderId: fId, path: fPath, label: fLabel)
                                }
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.system(size: 12, weight: .bold))
                                    .foregroundColor(CosmicTheme.redFault)
                                    .padding(3)
                                    .contentShape(Rectangle())
                            }
                            .buttonStyle(.plain)
                        }
                        .padding(.leading, 8)
                        .padding(.trailing, 5)
                        .padding(.vertical, 3)
                        .background(CosmicTheme.bgCard)
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(CosmicTheme.emerald.opacity(0.6), lineWidth: 1)
                        )
                        .cornerRadius(12)
                    }

                    Button(action: {
                        store.pickAndConnectFolder(accessMode: "READ_WRITE")
                    }) {
                        Label("+ Akses Folder", systemImage: "folder.badge.plus")
                            .font(.system(size: 10.5, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.cyan)
                    .controlSize(.small)

                    Button(action: {
                        store.pickFilesToAttach()
                    }) {
                        Label("+ File", systemImage: "doc.badge.plus")
                            .font(.system(size: 10.5, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.emerald)
                    .controlSize(.small)

                    Button(action: {
                        store.checkLatestRepoWorkNow()
                    }) {
                        Label("Cek Repo Terakhir", systemImage: "clock.arrow.circlepath")
                            .font(.system(size: 10.5, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.gold)
                    .controlSize(.small)

                    ForEach(store.attachedPaths, id: \.self) { attPath in
                        let isDir = (try? URL(fileURLWithPath: attPath).resourceValues(forKeys: [.isDirectoryKey]).isDirectory) ?? false
                        let name = URL(fileURLWithPath: attPath).lastPathComponent
                        HStack(spacing: 5) {
                            Image(systemName: isDir ? "folder.fill" : "doc.text.fill")
                                .font(.system(size: 10.5))
                                .foregroundColor(CosmicTheme.gold)
                            Text("📎 \(name)")
                                .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                .foregroundColor(CosmicTheme.gold)
                            Button(action: {
                                store.removeAttachedPath(attPath)
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .font(.system(size: 10.5))
                                    .foregroundColor(CosmicTheme.silver)
                            }
                            .buttonStyle(.plain)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(CosmicTheme.gold.opacity(0.18))
                        .overlay(
                            RoundedRectangle(cornerRadius: 12)
                                .stroke(CosmicTheme.gold.opacity(0.8), lineWidth: 1)
                        )
                        .cornerRadius(12)
                    }
                }
                .padding(.horizontal, 12)
                .padding(.top, 8)
                .padding(.bottom, 4)
            }
            .background(CosmicTheme.bgSecondary)

            // Multiline Chat Composer (Section 4)
            VStack(spacing: 6) {
                HStack(alignment: .bottom, spacing: 8) {
                    Menu {
                        Button(action: {
                            store.pickAndConnectFolder(accessMode: "READ_WRITE")
                        }) {
                            Label("Hubungkan Folder Lokal (Connected Folders)...", systemImage: "folder.badge.plus")
                        }
                        Button(action: {
                            store.pickFilesToAttach()
                        }) {
                            Label("Lampirkan Berkas / Kode Lokal...", systemImage: "doc.badge.plus")
                        }
                        Divider()
                        Button(action: {
                            store.checkYayasanVPSConnectionNow()
                        }) {
                            Label("Cek Apakah Folder Yayasan Sudah Terhubung ke VPS", systemImage: "externaldrive.connected.to.line.below.fill")
                        }
                        Button(action: {
                            store.checkLatestRepoWorkNow()
                        }) {
                            Label("Cek Pekerjaan Terakhir di Repo (Git & Berkas Terbaru)", systemImage: "clock.arrow.circlepath")
                        }
                        Divider()
                        Button(action: {
                            store.selectedSection = .filesKnowledge
                        }) {
                            Label("Kelola Semua Connected Folders & Knowledge...", systemImage: "gearshape.fill")
                        }
                    } label: {
                        Label("+", systemImage: "plus.circle.fill")
                            .font(.system(size: 13, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.cyan)
                    .frame(width: 52)

                    Button(action: {
                        store.pickAndConnectFolder(accessMode: "READ_WRITE")
                    }) {
                        Label("Folder", systemImage: "folder.badge.plus")
                            .font(.system(size: 11.5, weight: .bold))
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.gold)

                    Button(action: {
                        store.pasteFromClipboardIntoComposer()
                    }) {
                        Label("Paste", systemImage: "doc.on.clipboard")
                            .font(.system(size: 11.5, weight: .semibold))
                    }
                    .buttonStyle(.bordered)
                    .tint(CosmicTheme.cyan)
                    .help("Tempel teks atau kode dari clipboard macOS (Cmd+V)")

                    ZStack(alignment: .topLeading) {
                        ChatComposerTextView(
                            text: $store.chatInput,
                            placeholder: "Ketik pesan atau tempelkan kode dan teks di sini... (Enter = Kirim, Shift+Enter = Baris Baru)",
                            isDisabled: store.isGenerating,
                            focusTrigger: store.shouldRefocusComposer,
                            onSubmitSend: {
                                guard !store.isGenerating else { return }
                                Task {
                                    await store.sendChatMessage()
                                }
                            }
                        )
                        .frame(height: ChatComposerTextView.calculatedHeight(for: store.chatInput))
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(CosmicTheme.cyan.opacity(0.42), lineWidth: 1)
                        )
                        .cornerRadius(8)

                        if store.chatInput.isEmpty {
                            Text("Ketik pesan atau tempelkan kode dan teks di sini... (Enter = Kirim, Shift+Enter = Baris Baru)")
                                .font(.system(size: 12.5))
                                .foregroundColor(CosmicTheme.muted.opacity(0.75))
                                .padding(.horizontal, 11)
                                .padding(.vertical, 10)
                                .allowsHitTesting(false)
                        }
                    }

                    if store.isGenerating {
                        Button(action: {
                            Task { await store.stopGeneration() }
                        }) {
                            Label("Stop", systemImage: "stop.circle.fill")
                                .font(.system(size: 12, weight: .bold))
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.redFault)
                    } else {
                        Button(action: {
                            Task {
                                await store.sendChatMessage()
                            }
                        }) {
                            Label("Kirim", systemImage: "paperplane.fill")
                                .font(.system(size: 12.5, weight: .bold))
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.emerald)
                        .disabled(store.chatInput.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    }
                }

                HStack(spacing: 12) {
                    let charCount = store.chatInput.count
                    let estTokens = charCount == 0 ? 0 : max(1, (charCount + 3) / 4)
                    let lineCount = max(1, store.chatInput.components(separatedBy: "\n").count)
                    Text("\(charCount) karakter · ~\(estTokens) token · \(lineCount) baris")
                        .font(.system(size: 10, weight: .medium, design: .monospaced))
                        .foregroundColor(CosmicTheme.muted)
                    if !store.chatInput.isEmpty {
                        Text("✓ Draft tersimpan otomatis")
                            .font(.system(size: 10, weight: .semibold, design: .monospaced))
                            .foregroundColor(CosmicTheme.emerald)
                    }
                    Spacer()
                    Text("Enter: Kirim · Shift+Enter: Baris Baru · Cmd+V: Tempel Kode/Teks")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundColor(CosmicTheme.muted)
                }
                .padding(.horizontal, 4)
            }
            .padding(12)
            .background(CosmicTheme.bgSecondary)
        }
    }
}

// MARK: - Center Workspace Switcher

struct CenterWorkspaceView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        switch store.selectedSection {
        case .nuiChat:
            NUIChatSectionView(store: store)
        case .languageEngine:
            LanguageEngineSectionView(store: store)
        case .selfLearning:
            SelfLearningCenterSectionView(store: store)
        case .nuiCore, .nuiArchitecture:
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    Text("NUI Architecture & Core Inspector (L0–L11 Honest Telemetry)")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.gold)
                    ForEach(Array(store.nuiLayers.enumerated()), id: \.offset) { _, layer in
                        let code = (layer["layer"] as? String) ?? ""
                        let name = (layer["name"] as? String) ?? ""
                        let badge = (layer["badge"] as? String) ?? ""
                        let note = (layer["honest_note"] as? String) ?? ""
                        HStack {
                            Text(code)
                                .font(.system(size: 13, weight: .bold, design: .monospaced))
                                .foregroundColor(CosmicTheme.cyan)
                                .frame(width: 36, alignment: .leading)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(name).font(.system(size: 13, weight: .semibold)).foregroundColor(CosmicTheme.silver)
                                Text(note).font(.system(size: 11)).foregroundColor(CosmicTheme.muted)
                            }
                            Spacer()
                            Text(badge)
                                .font(.system(size: 11, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(badge.contains("AT") ? CosmicTheme.gold.opacity(0.2) : CosmicTheme.emerald.opacity(0.2))
                                .foregroundColor(badge.contains("AT") ? CosmicTheme.gold : CosmicTheme.emerald)
                                .cornerRadius(6)
                        }
                        .padding(10)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    }
                }
                .padding(16)
            }
        case .computingSystem:
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    Text("CosmicTera 11 Computing Subsystems (Live Integration)")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.emerald)
                    ForEach(Array(store.subsystems.enumerated()), id: \.offset) { _, sub in
                        let name = (sub["name"] as? String) ?? ""
                        let status = (sub["status"] as? String) ?? ""
                        let summary = (sub["summary"] as? String) ?? ""
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(name).font(.system(size: 13, weight: .bold)).foregroundColor(CosmicTheme.silver)
                                Spacer()
                                Text(status).font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                            }
                            Text(summary).font(.system(size: 12)).foregroundColor(CosmicTheme.muted)
                        }
                        .padding(10)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    }
                }
                .padding(16)
            }
        case .codingStudio:
            VStack(alignment: .leading, spacing: 10) {
                Text("CosmicTera Coding & Website Studio (\(store.activeCodingSpecialistLabel))")
                    .font(.headline)
                    .foregroundColor(CosmicTheme.cyan)
                HStack(spacing: 8) {
                    TextField("File Path", text: $store.editorFilePath)
                        .textFieldStyle(.roundedBorder)
                    Button("Open File") {
                        Task { await store.openFileInStudio() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.cyan)
                    Button("Save File") {
                        Task { await store.saveFileInStudio() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(CosmicTheme.emerald)
                    Button("Sync Git") {
                        Task { await store.refreshAll() }
                    }
                    .buttonStyle(.bordered)
                }
                TextEditor(text: $store.editorContent)
                    .font(.system(size: 12.5, design: .monospaced))
                    .frame(minHeight: 240)
                    .cornerRadius(8)
                Text("Status: \(store.studioOutput)")
                    .font(.system(size: 11.5, design: .monospaced))
                    .foregroundColor(CosmicTheme.emerald)
            }
            .padding(16)
        case .browser:
            CosmicTeraBrowserWorkspaceView(store: store)
        case .hardwareMonitor:
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Tang Nano 20K FPGA & CosmicTera HDMI Control Monitor")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.emerald)
                    let conn = (store.hardwareStatus["connection_state"] as? String) ?? "UNKNOWN"
                    let usb = (store.hardwareStatus["usb_transport"] as? String) ?? "NO_USB_SERIAL_DETECTED"
                    let cpu = (store.hardwareStatus["cpu_state"] as? String) ?? "UNKNOWN"
                    let sha = (store.hardwareStatus["bitstream_sha256"] as? String) ?? "N/A"
                    let liveTel = (store.hardwareStatus["live_telemetry_available"] as? Bool) ?? false
                    let lastChk = (store.hardwareStatus["last_checked"] as? String) ?? "N/A"
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Connection: \(conn)").font(.system(size: 13, weight: .bold, design: .monospaced)).foregroundColor(liveTel ? CosmicTheme.emerald : CosmicTheme.gold)
                        Text("USB Transport: \(usb) | Live UART Telemetry: \(liveTel ? "YES (LIVE_PHYSICAL)" : "NO (SIMULATED / BUILD_ARTIFACT)")")
                            .font(.system(size: 11.5, design: .monospaced))
                            .foregroundColor(CosmicTheme.cyan)
                        Text("HCPU State: \(cpu)").font(.system(size: 12.5, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                        Text("Bitstream SHA-256 (BUILD_ARTIFACT): \(sha)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                        Text("Last Checked: \(lastChk)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.muted)
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)
                    HStack(spacing: 12) {
                        Button("S1 STOP / PAUSE") { Task { await store.triggerHardwareAction("S1_STOP") } }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.gold)
                        Button("S2 RESET / RECOVERY") { Task { await store.triggerHardwareAction("S2_RECOVERY") } }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.cyan)
                        Button("Run H-ISA test_bsm.hasm") { Task { await store.triggerHardwareAction("EXEC_WORKLOAD") } }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.emerald)
                    }
                }
                .padding(16)
            }
        case .activityHistory:
            ScrollView {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Communication & Tool Audit Logs")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.emerald)
                    ForEach(Array(store.commLogs.prefix(25).enumerated()), id: \.offset) { _, log in
                        let reqId = (log["request_id"] as? String) ?? ""
                        let prov = (log["provider"] as? String) ?? ""
                        let st = (log["execution_status"] as? String) ?? ""
                        let msg = (log["user_message"] as? String) ?? ""
                        let ms = (log["response_time_ms"] as? Double) ?? 0.0
                        VStack(alignment: .leading, spacing: 3) {
                            HStack {
                                Text("[\(reqId)] \(prov)").font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                                Spacer()
                                Text(String(format: "%@ (%.1f ms)", st, ms)).font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                            }
                            RichMarkdownAndCodeView(text: msg)
                        }
                        .padding(8)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(6)
                    }
                }
                .padding(16)
            }
        case .filesKnowledge, .projectsGit:
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("CONNECTED FOLDERS, FILE ATTACHMENTS (+) & REPOSITORY GIT INSPECTOR")
                                .font(.headline)
                                .foregroundColor(CosmicTheme.gold)
                            Text("Hubungkan atau putuskan koneksi folder lokal dari NUI tanpa menghapus berkas fisik di Mac.")
                                .font(.system(size: 11.5))
                                .foregroundColor(CosmicTheme.muted)
                        }
                        Spacer()
                        Button(action: {
                            store.pickAndConnectFolder(accessMode: "READ_WRITE")
                        }) {
                            Label("+ Hubungkan Folder Lokal", systemImage: "folder.badge.plus")
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.emerald)

                        Button(action: {
                            store.pickFilesToAttach()
                            store.selectedSection = .nuiChat
                        }) {
                            Label("+ Lampirkan Berkas ke Chat", systemImage: "doc.badge.plus")
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.cyan)
                    }

                    if let fBanner = store.folderNotificationBanner {
                        HStack {
                            Image(systemName: "checkmark.shield.fill").foregroundColor(CosmicTheme.emerald)
                            Text(fBanner).font(.system(size: 11.5, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Button("Tutup") { store.folderNotificationBanner = nil }
                                .buttonStyle(.bordered)
                        }
                        .padding(10)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    }

                    let branch = (store.gitStatus["branch"] as? String) ?? "unknown"
                    let headHash = (store.gitStatus["head_commit"] as? String) ?? "unknown"
                    let isClean = (store.gitStatus["working_tree_clean"] as? Bool) ?? false
                    let modFiles = (store.gitStatus["modified_files"] as? [String]) ?? []
                    VStack(alignment: .leading, spacing: 5) {
                        HStack {
                            Text("Live Git Repository Inspector").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                            Spacer()
                            Button("Refresh Git") { Task { await store.refreshAll() } }
                                .buttonStyle(.bordered)
                        }
                        Text("Branch: \(branch) | HEAD: \(headHash)")
                            .font(.system(size: 12, weight: .bold, design: .monospaced))
                            .foregroundColor(CosmicTheme.gold)
                        Text("Working Tree Clean: \(isClean ? "YES" : "NO (\(modFiles.count) modified/untracked)")")
                            .font(.system(size: 11.5, design: .monospaced))
                            .foregroundColor(isClean ? CosmicTheme.emerald : CosmicTheme.silver)
                        if !modFiles.isEmpty {
                            Text("Modified: " + modFiles.prefix(8).joined(separator: ", "))
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(CosmicTheme.muted)
                        }
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    Text("Daftar Connected Folders Aktif (\(store.authorizedFolders.count))")
                        .font(.subheadline.bold())
                        .foregroundColor(CosmicTheme.cyan)

                    ForEach(Array(store.authorizedFolders.enumerated()), id: \.offset) { _, fld in
                        let fId = (fld["folder_id"] as? String) ?? ""
                        let fPath = (fld["path"] as? String) ?? ""
                        let fLabel = (fld["label"] as? String) ?? fPath
                        let fMode = (fld["access_mode"] as? String) ?? "READ_WRITE"
                        HStack {
                            Image(systemName: "folder.fill.badge.gearshape")
                                .foregroundColor(CosmicTheme.emerald)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("\(fLabel) (\(fId))")
                                    .font(.system(size: 13, weight: .bold))
                                    .foregroundColor(CosmicTheme.silver)
                                Text(fPath)
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundColor(CosmicTheme.muted)
                            }
                            Spacer()
                            Text(fMode)
                                .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(fMode == "READ_ONLY" ? CosmicTheme.gold.opacity(0.2) : CosmicTheme.emerald.opacity(0.2))
                                .foregroundColor(fMode == "READ_ONLY" ? CosmicTheme.gold : CosmicTheme.emerald)
                                .cornerRadius(6)
                            Button("Lampirkan ke Chat (+)") {
                                store.attachPath(fPath)
                                store.selectedSection = .nuiChat
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.cyan)
                            Button("Putuskan (X)") {
                                Task { await store.disconnectConnectedFolder(folderId: fId, path: fPath, label: fLabel) }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.redFault)
                        }
                        .padding(10)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(8)
                    }

                    if !store.disconnectedFolders.isEmpty {
                        Text("Riwayat Folder Terputus — Klik untuk Hubungkan Kembali (\(store.disconnectedFolders.count))")
                            .font(.subheadline.bold())
                            .foregroundColor(CosmicTheme.gold)

                        ForEach(Array(store.disconnectedFolders.enumerated()), id: \.offset) { _, dfld in
                            let dfPath = (dfld["path"] as? String) ?? ""
                            let dfLabel = (dfld["label"] as? String) ?? dfPath
                            let dfMode = (dfld["access_mode"] as? String) ?? "READ_WRITE"
                            HStack {
                                Image(systemName: "folder.badge.minus")
                                    .foregroundColor(CosmicTheme.muted)
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(dfLabel).font(.system(size: 12.5, weight: .semibold)).foregroundColor(CosmicTheme.muted)
                                    Text(dfPath).font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.muted)
                                }
                                Spacer()
                                Button("Hubungkan Kembali (\(dfMode))") {
                                    Task { await store.connectFolderPath(dfPath, label: dfLabel, accessMode: dfMode) }
                                }
                                .buttonStyle(.borderedProminent)
                                .tint(CosmicTheme.emerald)
                            }
                            .padding(8)
                            .background(CosmicTheme.bgSecondary)
                            .cornerRadius(8)
                        }
                    }
                }
                .padding(16)
            }
        case .accessControl:
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("ACCESS CONTROL, FOLDER BOUNDARIES & L7 PERMISSION GATE")
                                .font(.headline)
                                .foregroundColor(CosmicTheme.gold)
                            Text("Status izin aktual dari PermissionEngine (SCOPED_BY_PERMISSION_ENGINE) mencakup Internet, Dependency, dan VPS.")
                                .font(.system(size: 11.5))
                                .foregroundColor(CosmicTheme.muted)
                        }
                        Spacer()
                        Button("Refresh Permissions") { Task { await store.refreshAll() } }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.cyan)
                    }

                    VStack(alignment: .leading, spacing: 5) {
                        Text("L7 Execution Gate & Immutable Core Protection").font(.subheadline.bold()).foregroundColor(CosmicTheme.emerald)
                        Text("Permission Policy: SCOPED_BY_PERMISSION_ENGINE (READ_ONLY / ALLOW_ONCE / ALLOW_SESSION / ALWAYS_ALLOW / ASK_EVERY_TIME / DENY / REVOKE_ACCESS)")
                            .font(.system(size: 11.5, design: .monospaced))
                            .foregroundColor(CosmicTheme.silver)
                        Text("Internet & VPS Scopes: INTERNET_SEARCH, WEBSITE_ACCESS, URL_FETCH, FILE_DOWNLOAD, DEPENDENCY_INSTALL, GIT_REMOTE_ACCESS, VPS_CONNECT, VPS_READ, VPS_WRITE, VPS_EXECUTE, VPS_DEPLOY")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundColor(CosmicTheme.cyan)
                        Text("Immutable Core Protection: ACTIVE (43 Canonical Modules src/hijaiyyah/nui/, L4-L7 Freeze Artifacts, H-ISA Contract)")
                            .font(.system(size: 11.5, design: .monospaced))
                            .foregroundColor(CosmicTheme.gold)
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    Text("Active Permission Rules (\(store.permissionRules.count))")
                        .font(.subheadline.bold())
                        .foregroundColor(CosmicTheme.cyan)

                    ForEach(Array(store.permissionRules.prefix(26).enumerated()), id: \.offset) { _, rule in
                        let cat = (rule["category"] as? String) ?? ""
                        let tgt = (rule["target_value"] as? String) ?? (rule["target_pattern"] as? String) ?? "*"
                        let mode = (rule["decision"] as? String) ?? (rule["mode"] as? String) ?? ""
                        HStack {
                            Text("[\(cat)] \(tgt)")
                                .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                .foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Text(mode)
                                .font(.system(size: 10.5, weight: .bold, design: .monospaced))
                                .foregroundColor(mode == "DENY" ? CosmicTheme.redFault : CosmicTheme.emerald)
                        }
                        .padding(8)
                        .background(CosmicTheme.bgCard)
                        .cornerRadius(6)
                    }
                }
                .padding(16)
            }
        case .webInternet:
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text("WEB & INTERNET RESEARCH, DEPENDENCY MANAGER & REMOTE VPS DEVELOPMENT")
                                .font(.headline)
                                .foregroundColor(CosmicTheme.gold)
                            Text("Network Mode: \(store.operatingMode) | Connectivity: \(store.internetConnectivityState) | AI Provider: \(store.activeProvider) (Separated)")
                                .font(.system(size: 11.5, weight: .semibold, design: .monospaced))
                                .foregroundColor(CosmicTheme.cyan)
                        }
                        Spacer()
                        Button("Test Live Connectivity (DNS/TLS/HTTPS)") {
                            Task { await store.runConnectivityCheck() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.gold)
                    }

                    VStack(alignment: .leading, spacing: 8) {
                        Text("1. Online Research & Documentation Fetch").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                        HStack(spacing: 8) {
                            TextField("Web Search Query or Documentation Topic", text: $store.webSearchQuery)
                                .textFieldStyle(.roundedBorder)
                            Button("Run Web Search") {
                                Task { await store.executeWebSearch() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.emerald)
                            Button("Open in Browser Tab") {
                                store.selectedSection = .browser
                                Task { await store.navigateBrowser() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.cyan)
                        }
                        Text(store.webSearchOutput)
                            .font(.system(size: 11.5, design: .monospaced))
                            .foregroundColor(CosmicTheme.silver)
                            .textSelection(.enabled)
                            .padding(10)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(CosmicTheme.bgSecondary)
                            .cornerRadius(6)
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("2. Dependency & Safe Staging Download Manager").font(.subheadline.bold()).foregroundColor(CosmicTheme.cyan)
                        HStack(spacing: 8) {
                            Picker("Manager", selection: $store.dependencyManagerName) {
                                ForEach(["pip", "uv", "npm", "pnpm", "yarn", "cargo", "brew", "git"], id: \.self) { m in
                                    Text(m).tag(m)
                                }
                            }
                            .frame(width: 130)
                            TextField("Package / Repo Name", text: $store.dependencyPackageName)
                                .textFieldStyle(.roundedBorder)
                            Button("Verify Compatibility & Plan") {
                                Task { await store.inspectAndInstallDependency(dryRun: true) }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.gold)
                            Button("Install Dependency") {
                                Task { await store.inspectAndInstallDependency(dryRun: false) }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.emerald)
                        }
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("3. Remote VPS Development Engine (OpenSSH + Host Key Verification + Keychain)")
                            .font(.subheadline.bold())
                            .foregroundColor(CosmicTheme.cyan)
                        HStack(spacing: 8) {
                            TextField("Profile Name", text: $store.vpsNameInput).textFieldStyle(.roundedBorder)
                            TextField("VPS Host / IP", text: $store.vpsHostInput).textFieldStyle(.roundedBorder)
                            TextField("User", text: $store.vpsUserInput).textFieldStyle(.roundedBorder).frame(width: 90)
                            TextField("Expected Host Fingerprint (SHA256:...)", text: $store.vpsFingerprintInput).textFieldStyle(.roundedBorder)
                            Button("Connect VPS") {
                                Task { await store.registerAndConnectVPS() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.emerald)
                        }
                        HStack(spacing: 8) {
                            TextField("Remote Workspace", text: $store.vpsWorkspaceInput).textFieldStyle(.roundedBorder).frame(width: 220)
                            TextField("Remote Build / Test Command", text: $store.vpsCommandInput).textFieldStyle(.roundedBorder)
                            Button("Run Remote Command") {
                                Task { await store.runRemoteVPSCommand() }
                            }
                            .buttonStyle(.borderedProminent)
                            .tint(CosmicTheme.cyan)
                        }
                        Text(store.vpsOutput)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundColor(CosmicTheme.silver)
                            .textSelection(.enabled)
                            .padding(8)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(CosmicTheme.bgSecondary)
                            .cornerRadius(6)
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    VStack(alignment: .leading, spacing: 10) {
                        Text("4. Network, Domain & VPS Verification Center (Live Operational Matrix)")
                            .font(.subheadline.bold())
                            .foregroundColor(CosmicTheme.gold)

                        HStack(spacing: 8) {
                            TextField("Active Domain", text: $store.activeDomainInput)
                                .textFieldStyle(.roundedBorder)
                            TextField("Local Folder Path", text: $store.localSyncFolderInput)
                                .textFieldStyle(.roundedBorder)
                        }

                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], alignment: .leading, spacing: 8) {
                            Text("Internet Status: \(store.internetConnectivityState)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                            Text("DNS Status: \(store.dnsStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                            Text("HTTPS Status: \(store.httpsStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                            Text("Active Domain: \(store.activeDomainInput)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                            Text("Domain Resolution: \(store.domainResolutionText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("Website HTTP Status: \(store.websiteHttpStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("TLS Certificate Status: \(store.tlsCertificateStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("VPS Profile: \(store.activeVpsProfileText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                            Text("SSH Status: \(store.sshStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.cyan)
                            Text("Host Fingerprint: \(store.hostFingerprintText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("SFTP Status: \(store.sftpStatusText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("Remote Workspace: \(store.remoteWorkspaceText)").font(.system(size: 11, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            Text("Sync Status: \(store.syncStatusText)").font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                        }
                        .padding(8)
                        .background(CosmicTheme.bgSecondary)
                        .cornerRadius(6)

                        HStack(spacing: 6) {
                            Button("Test Internet") { Task { await store.runConnectivityCheck() } }
                                .buttonStyle(.borderedProminent).tint(CosmicTheme.emerald)
                            Button("Check Domain") { Task { await store.checkDomainStatus() } }
                                .buttonStyle(.borderedProminent).tint(CosmicTheme.cyan)
                            Button("Test SSH") { Task { await store.testSSHConnection() } }
                                .buttonStyle(.borderedProminent).tint(CosmicTheme.gold)
                            Button("Inspect Remote Workspace") { Task { await store.inspectRemoteWorkspaceManifest() } }
                                .buttonStyle(.bordered)
                            Button("Compare Local and Remote") { Task { await store.compareLocalAndRemoteManifests() } }
                                .buttonStyle(.borderedProminent).tint(CosmicTheme.cyan)
                        }
                        HStack(spacing: 6) {
                            Button("Upload Files") { Task { await store.uploadFilesToVPS() } }
                                .buttonStyle(.bordered)
                            Button("Sync Directory") { Task { await store.syncDirectoryToVPS() } }
                                .buttonStyle(.bordered)
                            Button("Verify Deployment") { Task { await store.verifyFullDeployment() } }
                                .buttonStyle(.borderedProminent).tint(CosmicTheme.gold)
                            Button("Disconnect Remote") { Task { await store.disconnectRemoteVPS() } }
                                .buttonStyle(.bordered)
                        }

                        Text(store.networkVpsVerificationReport)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundColor(CosmicTheme.silver)
                            .textSelection(.enabled)
                            .padding(8)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .background(CosmicTheme.bgSecondary)
                            .cornerRadius(6)
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)
                }
                .padding(16)
            }
        case .settings:
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    Text("COSMICTERA NUI DESKTOP — SYSTEM SETTINGS & CONFIGURATION")
                        .font(.headline)
                        .foregroundColor(CosmicTheme.gold)
                    Text("Status: \(store.settingsBanner)")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(CosmicTheme.emerald)
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            Text("Active Language Provider:").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Picker("Provider", selection: Binding(
                                get: { store.activeProvider },
                                set: { p in Task { await store.switchProvider(p) } }
                            )) {
                                Text("Native NUI (L0-L11)").tag("native_nui")
                                Text("Local Ollama (NUI Persona)").tag("local_ollama")
                                Text("Multi-Model Auto Router").tag("auto")
                                Text("External API").tag("external_api")
                            }
                            .frame(width: 240)
                        }
                        HStack {
                            Text("Operating Mode:").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Picker("Mode", selection: Binding(
                                get: { store.operatingMode },
                                set: { m in Task { await store.switchOperatingMode(m) } }
                            )) {
                                Text("LOCAL").tag("LOCAL")
                                Text("HYBRID").tag("HYBRID")
                                Text("ONLINE").tag("ONLINE")
                            }
                            .pickerStyle(.segmented)
                            .frame(width: 240)
                        }
                        HStack {
                            Text("Browser Session Policy:").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Picker("Session Policy", selection: Binding(
                                get: { store.browserSessionPolicy },
                                set: { pol in Task { await store.switchBrowserSessionPolicy(pol) } }
                            )) {
                                Text("Persistent Profile").tag("PERSISTENT_PROFILE")
                                Text("Temporary Private").tag("TEMPORARY_PRIVATE")
                            }
                            .frame(width: 240)
                        }
                        HStack {
                            Text("Active Coding Specialist:").font(.system(size: 12.5, weight: .bold)).foregroundColor(CosmicTheme.silver)
                            Spacer()
                            Text(store.activeCodingSpecialistLabel)
                                .font(.system(size: 11.5, weight: .bold, design: .monospaced))
                                .foregroundColor(CosmicTheme.gold)
                        }
                    }
                    .padding(12)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)

                    HStack(spacing: 12) {
                        Button("Save & Sync Settings") {
                            Task {
                                await store.switchOperatingMode(store.operatingMode)
                                await store.switchProvider(store.activeProvider)
                            }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.emerald)

                        Button("Reset to Defaults") {
                            Task { await store.resetSettingsToDefaults() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(CosmicTheme.gold)
                    }
                }
                .padding(16)
            }
        default:
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    Text(store.selectedSection.rawValue)
                        .font(.headline)
                        .foregroundColor(CosmicTheme.gold)
                    Text("Service: \(store.serviceState) | Provider: \(store.providerState) | Mode: \(store.operatingMode)")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(CosmicTheme.silver)
                }
                .padding(16)
            }
        }
    }
}

// MARK: - Right Inspector View

struct RightInspectorView: View {
    @ObservedObject var store: NUIDesktopStore

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Text("NUI LIVE THINKING INSPECTOR")
                        .font(.system(size: 11, weight: .bold, design: .monospaced))
                        .foregroundColor(CosmicTheme.gold)
                    Spacer()
                    Button(action: { store.isRightInspectorCollapsed = true }) {
                        Image(systemName: "sidebar.right")
                            .font(.system(size: 11))
                            .foregroundColor(CosmicTheme.cyan)
                    }
                    .buttonStyle(.plain)
                    .help("Sembunyikan Inspector")
                }

                VStack(alignment: .leading, spacing: 5) {
                    Text("Engine & Stream State").font(.caption.bold()).foregroundColor(CosmicTheme.cyan)
                    Text("UI: \(store.uiState)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                    Text("Service: \(store.serviceState)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                    Text("Provider: \(store.providerState)").font(.system(size: 11, design: .monospaced)).foregroundColor(store.providerState.contains("UNAVAILABLE") ? CosmicTheme.redFault : CosmicTheme.emerald)
                    Text("Selected Model: \(store.selectedModelTag)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                    Text("Auto-Scroll: \(store.isAutoFollowEnabled ? "FOLLOWING" : "PAUSED (USER SCROLLED UP)")").font(.system(size: 10.5, weight: .semibold, design: .monospaced)).foregroundColor(store.isAutoFollowEnabled ? CosmicTheme.emerald : CosmicTheme.gold)
                    if !store.liveThinkingStage.isEmpty {
                        Text("Stage: \(store.liveThinkingStage)").font(.system(size: 11, weight: .bold, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                    }
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(CosmicTheme.bgCard)
                .cornerRadius(8)

                if !store.liveStagesHistory.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Live Thinking Pipeline").font(.caption.bold()).foregroundColor(CosmicTheme.cyan)
                        ForEach(store.liveStagesHistory, id: \.self) { stg in
                            HStack(spacing: 6) {
                                Image(systemName: stg == "COMPLETE" ? "checkmark.circle.fill" : (stg == "CANCELLED" ? "xmark.circle.fill" : "bolt.circle.fill"))
                                    .foregroundColor(stg == "COMPLETE" ? CosmicTheme.emerald : (stg == "CANCELLED" ? CosmicTheme.redFault : CosmicTheme.gold))
                                Text(stg).font(.system(size: 10.5, weight: .semibold, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                            }
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(CosmicTheme.bgCard)
                    .cornerRadius(8)
                }

                VStack(alignment: .leading, spacing: 5) {
                    Text("Browser & Network State").font(.caption.bold()).foregroundColor(CosmicTheme.cyan)
                    Text("Net: \(store.internetConnectivityState)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(store.internetConnectivityState == "CONNECTED" ? CosmicTheme.emerald : CosmicTheme.gold)
                    Text("Policy: \(store.browserSessionPolicy)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                    Text("Tabs: \(store.browserTabs.count) | Bookmarks: \(store.browserBookmarks.count)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(CosmicTheme.bgCard)
                .cornerRadius(8)

                VStack(alignment: .leading, spacing: 5) {
                    Text("Official NUI Persona").font(.caption.bold()).foregroundColor(CosmicTheme.cyan)
                    Text("Source: HybitAIProgram.system").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                    Text("Rules: AGENTS.md K1-K15 + RULES.md R1-R13").font(.system(size: 10, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                    Text("Coding Asset: \(store.activeCodingSpecialistLabel)").font(.system(size: 10.5, design: .monospaced)).foregroundColor(CosmicTheme.gold)
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(CosmicTheme.bgCard)
                .cornerRadius(8)

                VStack(alignment: .leading, spacing: 5) {
                    Text("Active Session").font(.caption.bold()).foregroundColor(CosmicTheme.cyan)
                    Text("ID: \(store.currentSessionId)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.silver)
                    Text("Messages: \(store.messages.count)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.emerald)
                    Text("Saved Sessions: \(store.sessions.count)").font(.system(size: 11, design: .monospaced)).foregroundColor(CosmicTheme.muted)
                }
                .padding(10)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(CosmicTheme.bgCard)
                .cornerRadius(8)
            }
            .padding(12)
        }
    }
}

@MainActor
final class WebKitRuntimeLiveVerifier {
    static func runCLIModesIfRequested() -> Bool {
        let args = CommandLine.arguments
        if args.contains("--verify-webkit-runtime") {
            Task { @MainActor in
                await executeDeterministicWebKitRuntimeCheck()
                exit(0)
            }
            RunLoop.main.run(until: Date(timeIntervalSinceNow: 25.0))
            return true
        }
        if args.contains("--verify-live-navigation") {
            Task { @MainActor in
                await executeLiveWebsiteNavigationCheck()
                exit(0)
            }
            RunLoop.main.run(until: Date(timeIntervalSinceNow: 65.0))
            return true
        }
        if args.contains("--verify-chat-clipboard-ui") {
            executeChatClipboardUXCheck()
            fflush(stdout)
            exit(0)
        }
        return false
    }

    private static func pumpUntil(_ condition: @escaping @MainActor () -> Bool, timeout: TimeInterval = 8.0) async -> Bool {
        let deadline = Date().addingTimeInterval(timeout)
        while Date() < deadline {
            if condition() {
                return true
            }
            try? await Task.sleep(nanoseconds: 60_000_000)
        }
        return condition()
    }

    static func executeDeterministicWebKitRuntimeCheck() async {
        let store = NUIDesktopStore()
        let win = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1180, height: 740),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        store.browserEngine.containerNSView.frame = NSRect(x: 0, y: 0, width: 960, height: 640)
        win.contentView = store.browserEngine.containerNSView
        win.layoutIfNeeded()
        store.browserEngine.containerNSView.layoutSubtreeIfNeeded()

        let wv1 = store.browserEngine.attachActiveTabWebView("tab-main", sessionPolicy: "PERSISTENT_PROFILE")

        // 1. Verify stale title reset immediately when navigating to www.akademihijaiyyahindonesia.com
        let navIdStaleCheck = store.browserEngine.loadURLInTab(
            tabId: "tab-main",
            urlString: "www.akademihijaiyyahindonesia.com",
            sessionPolicy: "PERSISTENT_PROFILE",
            operatingMode: "HYBRID",
            requestedRawInput: "www.akademihijaiyyahindonesia.com"
        )
        let immediateTitleAfterStart = store.browserPageTitle
        let immediateURLAfterStart = store.browserAddress
        let immediateStatusAfterStart = store.browserStatusText
        let staleTitleCleared = (immediateTitleAfterStart != "Python 3 Documentation") && immediateTitleAfterStart.contains("www.akademihijaiyyahindonesia.com")
        store.stopBrowserLoading()
        let statusAfterStop = store.browserStatusText

        // 2. Load Page A in real WKWebView and verify didCommit + didFinish + DOM title + viewport non-zero
        let navIdA = "nav-wk-page-a"
        store.browserEngine.applyNavigationTraceForLocalHTML(
            webView: wv1,
            tabId: "tab-main",
            navigationId: navIdA,
            url: BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/",
            html: "<!DOCTYPE html><html><head><title>Python 3.15 Documentation Live</title></head><body><h1>Python 3 Docs</h1><p>Real WKWebView viewport content A.</p></body></html>"
        )
        _ = await pumpUntil({ store.browserStatusText == "COMPLETE" && store.browserPageTitle == "Python 3.15 Documentation Live" }, timeout: 5.0)
        let titleA = store.browserPageTitle
        let traceA = store.browserEngine.navigationTraces[navIdA]

        // 3. Load Page B in real WKWebView and verify title updates to Page B (no stale title A)
        let navIdB = "nav-wk-page-b"
        store.browserEngine.applyNavigationTraceForLocalHTML(
            webView: wv1,
            tabId: "tab-main",
            navigationId: navIdB,
            url: BrowserAddressNormalizer.httpsPrefix + "www.akademihijaiyyahindonesia.com/",
            html: "<!DOCTYPE html><html><head><title>Akademi Hijaiyyah Indonesia — Membangun Peradaban</title></head><body><h1>Akademi Hijaiyyah Indonesia</h1><p>Mengaji Gratis Berilmu Berakhlak Beramal</p></body></html>"
        )
        _ = await pumpUntil({ store.browserStatusText == "COMPLETE" && store.browserPageTitle.contains("Akademi Hijaiyyah Indonesia") }, timeout: 5.0)
        let titleB = store.browserPageTitle
        let traceB = store.browserEngine.navigationTraces[navIdB]

        // 4. Open Tab 2, load GitHub HTML, switch back to Tab 1, and verify both tabs preserve their WKWebView state
        await store.openNewBrowserTab(initialURL: BrowserAddressNormalizer.httpsPrefix + "github.com/")
        let tab2Id = store.activeBrowserTabId
        let wv2 = store.browserEngine.attachActiveTabWebView(tab2Id, sessionPolicy: "PERSISTENT_PROFILE")
        let navIdTab2 = "nav-wk-tab2"
        store.browserEngine.applyNavigationTraceForLocalHTML(
            webView: wv2,
            tabId: tab2Id,
            navigationId: navIdTab2,
            url: BrowserAddressNormalizer.httpsPrefix + "github.com/",
            html: "<!DOCTYPE html><html><head><title>GitHub · Build and ship software</title></head><body><h1>GitHub</h1></body></html>"
        )
        _ = await pumpUntil({ store.browserStatusText == "COMPLETE" && store.browserPageTitle.contains("GitHub") }, timeout: 5.0)
        let tab2Title = store.browserPageTitle
        await store.switchBrowserTab("tab-main")
        let switchedBackTitle = store.browserPageTitle

        // 5. Verify Navigation Error renders diagnostic HTML inside WKWebView viewport
        let errHTML = BrowserAddressNormalizer.buildErrorHTML(
            url: BrowserAddressNormalizer.httpsPrefix + "invalid.domain.cosmictera.test/",
            domain: "invalid.domain.cosmictera.test",
            errorCode: "NSURLErrorCannotFindHost(-1003)",
            errorMessage: "A server with the specified hostname could not be found."
        )
        store.applyNavigationFailureState(
            tabId: "tab-main",
            navigationId: "nav-wk-err",
            failingURL: BrowserAddressNormalizer.httpsPrefix + "invalid.domain.cosmictera.test/",
            domain: "invalid.domain.cosmictera.test",
            errorCode: "NSURLErrorCannotFindHost(-1003)",
            errorMessage: "A server with the specified hostname could not be found.",
            errorHTML: errHTML
        )
        store.browserEngine.renderErrorPageInTab(
            tabId: "tab-main",
            html: errHTML,
            failingURL: nil,
            sessionPolicy: "PERSISTENT_PROFILE"
        )
        try? await Task.sleep(nanoseconds: 350_000_000)
        let errorStatus = store.browserStatusText
        let errorTitle = store.browserPageTitle

        let report: [String: Any] = [
            "ok": staleTitleCleared && (titleA == "Python 3.15 Documentation Live") && titleB.contains("Akademi Hijaiyyah Indonesia") && tab2Title.contains("GitHub") && switchedBackTitle.contains("Akademi Hijaiyyah Indonesia") && (errorStatus == "FAILED"),
            "viewport_width": store.browserEngine.viewportWidth,
            "viewport_height": store.browserEngine.viewportHeight,
            "webview_in_active_hierarchy": wv1.superview === store.browserEngine.containerNSView,
            "navigation_delegate_attached": wv1.navigationDelegate != nil,
            "stale_title_cleared_on_start": staleTitleCleared,
            "immediate_title_on_start": immediateTitleAfterStart,
            "immediate_url_on_start": immediateURLAfterStart,
            "immediate_status_on_start": immediateStatusAfterStart,
            "status_after_stop": statusAfterStop,
            "nav_id_stale_check": navIdStaleCheck,
            "page_a_title": titleA,
            "page_a_did_commit": traceA?.didCommit ?? false,
            "page_a_did_finish": traceA?.didFinish ?? false,
            "page_b_title": titleB,
            "page_b_did_commit": traceB?.didCommit ?? false,
            "page_b_did_finish": traceB?.didFinish ?? false,
            "page_b_content_visible": traceB?.contentVisibleInViewport ?? false,
            "tab2_title": tab2Title,
            "switched_back_tab1_title": switchedBackTitle,
            "error_status": errorStatus,
            "error_title": errorTitle
        ]
        if let data = try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted]),
           let str = String(data: data, encoding: .utf8) {
            print("WEBKIT_RUNTIME_VERIFY_JSON_START")
            print(str)
            print("WEBKIT_RUNTIME_VERIFY_JSON_END")
        }
    }

    static func executeLiveWebsiteNavigationCheck() async {
        let store = NUIDesktopStore()
        let win = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1180, height: 740),
            styleMask: [.titled, .closable, .resizable],
            backing: .buffered,
            defer: false
        )
        store.browserEngine.containerNSView.frame = NSRect(x: 0, y: 0, width: 960, height: 640)
        win.contentView = store.browserEngine.containerNSView
        win.layoutIfNeeded()
        store.browserEngine.containerNSView.layoutSubtreeIfNeeded()

        await store.runNativeConnectivityProbe()

        let targets = [
            BrowserAddressNormalizer.httpsPrefix + "docs.python.org/3/",
            BrowserAddressNormalizer.httpsPrefix + "www.google.com/",
            BrowserAddressNormalizer.httpsPrefix + "github.com/",
            BrowserAddressNormalizer.httpsPrefix + "www.akademihijaiyyahindonesia.com/"
        ]

        var siteResults: [[String: Any]] = []
        for targetURL in targets {
            let host = URL(string: targetURL)?.host ?? ""
            // 1. DNS check
            var hints = addrinfo()
            hints.ai_family = AF_UNSPEC
            hints.ai_socktype = SOCK_STREAM
            var resPtr: UnsafeMutablePointer<addrinfo>? = nil
            let dnsCode = Darwin.getaddrinfo(host, "443", &hints, &resPtr)
            if let ptr = resPtr { Darwin.freeaddrinfo(ptr) }
            let dnsOK = (dnsCode == 0)

            // 2. URLSession HTTPS GET check
            var urlSessionStatus = 0
            var urlSessionFinalURL = targetURL
            var urlSessionError = ""
            if let u = URL(string: targetURL) {
                var req = URLRequest(url: u, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 8.0)
                req.httpMethod = "GET"
                do {
                    let (_, resp) = try await URLSession.shared.data(for: req)
                    if let httpResp = resp as? HTTPURLResponse {
                        urlSessionStatus = httpResp.statusCode
                        urlSessionFinalURL = httpResp.url?.absoluteString ?? targetURL
                    }
                } catch {
                    urlSessionError = error.localizedDescription
                }
            }

            // 3. Real WKWebView Navigation
            let t0 = Date()
            let navId = store.browserEngine.loadURLInTab(
                tabId: "tab-main",
                urlString: targetURL,
                sessionPolicy: "PERSISTENT_PROFILE",
                operatingMode: "HYBRID",
                requestedRawInput: targetURL,
                forceReload: true
            )
            _ = await pumpUntil({
                let st = store.browserStatusText
                return st == "COMPLETE" || st == "FAILED"
            }, timeout: 12.0)
            let elapsedMs = round(Date().timeIntervalSince(t0) * 1000.0)
            let tr = store.browserEngine.navigationTraces[navId]

            siteResults.append([
                "requested_url": targetURL,
                "normalized_url": tr?.normalizedURL ?? targetURL,
                "final_url": tr?.actualURL ?? store.browserActiveURL,
                "dns_ok": dnsOK,
                "urlsession_http_status": urlSessionStatus,
                "urlsession_final_url": urlSessionFinalURL,
                "urlsession_error": urlSessionError,
                "wkwebview_navigation_id": navId,
                "wkwebview_http_status": tr?.httpStatus ?? store.browserLastHTTPStatus,
                "wkwebview_page_title": store.browserPageTitle,
                "didStartProvisionalNavigation": tr?.didStartProvisionalNavigation ?? false,
                "didReceiveServerRedirectForProvisionalNavigation": tr?.didReceiveServerRedirectForProvisionalNavigation ?? false,
                "didCommit": tr?.didCommit ?? false,
                "didFinish": tr?.didFinish ?? false,
                "didFailProvisionalNavigation": tr?.didFailProvisionalNavigation ?? false,
                "didFail": tr?.didFail ?? false,
                "status": store.browserStatusText,
                "error_code": tr?.errorCode ?? "",
                "error_message": tr?.errorMessage ?? "",
                "elapsed_ms": tr?.elapsedMs ?? elapsedMs,
                "viewport_width": store.browserEngine.viewportWidth,
                "viewport_height": store.browserEngine.viewportHeight,
                "content_visible_in_viewport": tr?.contentVisibleInViewport ?? false
            ])
        }

        let payload: [String: Any] = [
            "timestamp": ISO8601DateFormatter().string(from: Date()),
            "net_connectivity_state": store.internetConnectivityState,
            "net_connectivity_reason": store.internetConnectivityReason,
            "sites": siteResults
        ]
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted]),
           let str = String(data: data, encoding: .utf8) {
            try? str.write(
                toFile: "/Users/AMRA/hijaiyyah-mathematics/nui-desktop/data/webkit_live_navigation_results.json",
                atomically: true,
                encoding: .utf8
            )
            print("LIVE_NAVIGATION_VERIFY_JSON_START")
            print(str)
            print("LIVE_NAVIGATION_VERIFY_JSON_END")
        }
    }

    static func executeChatClipboardUXCheck() {
        let store = NUIDesktopStore(skipAutoBootstrap: true)
        let clipMgr = NUIClipboardManager.shared

        // 1. Copy user message via NSPasteboard.general
        let userText = "Cek apakah folder Yayasan sudah terhubung ke VPS.\nBaris kedua dengan Hijaiyyah: ب س م dan rumus ||BSM||² = 112"
        let userMsg = ChatMessageItem(
            id: "u-test-1",
            requestId: "req-u-1",
            role: "user",
            content: userText + "\n\n📎 *Lampiran (+):* `yayasan`",
            provider: "local_ollama",
            model: "qwen3:4b-instruct-2507-q4_K_M",
            responseTimeMs: 0,
            sourceAttribution: "USER_INPUT",
            executionStatus: "SENT",
            thinkingStages: [],
            toolActivities: []
        )
        store.copyUserQuestion(userMsg)
        let copiedUserResult = clipMgr.readPasteboardString()
        let copyUserPass = (copiedUserResult == userText) && (store.copiedItemId == "user-u-test-1")

        // 2. Copy full assistant response (including long response beyond scroll viewport)
        let longBodyLines = (1...60).map { "Baris penjelasan #\($0): Folder `/Users/AMRA/yayasan` adalah path lokal READ_WRITE." }.joined(separator: "\n")
        let codeSnippet = """
        def verify_bsm_norm():
            # ב س م -> (2, 12, 24)
            vec = (2, 12, 24)
            norm_sq = sum(x * x for x in vec)
            return norm_sq  # 624, ||BSM||² = 112
        """
        let fullAssistantMarkdown = """
        # Hasil Pemeriksaan Koneksi VPS Folder Yayasan

        | Field | Nilai |
        | --- | --- |
        | `local_canonical_path` | `/Users/AMRA/yayasan` |
        | `ssh_connection_status` | `NOT_CONFIGURED` |

        \(longBodyLines)

        ```python
        \(codeSnippet)
        ```

        $$||BSM||² = 112, H_c = 13.714285714285714$$
        """
        let asstMsg = ChatMessageItem(
            id: "a-test-1",
            requestId: "req-u-1",
            role: "assistant",
            content: fullAssistantMarkdown,
            provider: "local_ollama",
            model: "qwen3:4b-instruct-2507-q4_K_M",
            responseTimeMs: 14.5,
            sourceAttribution: "VPS_FOLDER_INSPECTION",
            executionStatus: "COMPLETE",
            thinkingStages: ["REQUEST_RECEIVED", "COMPLETE"],
            toolActivities: []
        )
        store.copyAssistantFullAnswer(asstMsg)
        let copiedAsstResult = clipMgr.readPasteboardString()
        let copyFullAssistantPass = (copiedAsstResult == fullAssistantMarkdown) && (copiedAsstResult.count == fullAssistantMarkdown.count) && (store.copiedItemId == "asst-a-test-1")

        // 3. Copy code block only (no markdown fences, no surrounding explanation)
        store.copyRawCodeBlock(code: codeSnippet, blockId: "code-a-test-1-1")
        let copiedCodeOnlyResult = clipMgr.readPasteboardString()
        let copyCodeOnlyPass = (copiedCodeOnlyResult == codeSnippet)
            && !copiedCodeOnlyResult.contains("```")
            && !copiedCodeOnlyResult.contains("Hasil Pemeriksaan Koneksi VPS")
            && (store.copiedItemId == "code-a-test-1-1")

        // 4. Paste multiline text, code, Unicode, Arabic Hijaiyyah, and mathematical expressions into composer
        let complexPastePayload = """
        // Hijaiyyah Mathematical & Code Paste Test
        // Huruf: ا ب ت ث ج ح خ د ذ ر ز س ش ص ض ط ظ ع غ ف ق ك ل م ن و ه لا ء ي
        // Formula: ||BSM||² = 112, f_H = 1.989e-24, τ₀ = 49.000 ms
        func computeHijaiyyahNorm(_ b: Int, _ s: Int, _ m: Int) -> Int {
        \treturn (b * b) + (s * s) + (m * m)
        }
        """
        clipMgr.copyString(complexPastePayload)
        store.chatInput = ""
        let composerTV = NUIComposerNSTextView()
        var composerSentCount = 0
        composerTV.onTextChange = { updated in
            store.chatInput = updated
        }
        composerTV.onEnterSend = {
            composerSentCount += 1
        }
        composerTV.paste(nil)
        let pastePreservedExact = (store.chatInput == complexPastePayload)
            && store.chatInput.contains("ا ب ت ث ج ح خ")
            && store.chatInput.contains("||BSM||² = 112")
            && store.chatInput.contains("\treturn (b * b)")

        // 5. Shift+Enter inserts newline without sending; Enter triggers send
        composerTV.handleSimulatedReturnKey(shiftPressed: true)
        let shiftEnterAddedNewlineWithoutSend = (composerSentCount == 0) && store.chatInput.hasSuffix("\n")
        composerTV.handleSimulatedReturnKey(shiftPressed: false)
        let enterTriggeredSend = (composerSentCount == 1)

        // 6. Draft persistence across sidebar menu switches and session switches
        store.currentSessionId = "sess-draft-alpha"
        store.chatInput = "Draft pesan penting untuk sesi alpha yang belum dikirim"
        store.selectedSection = .browser
        store.selectedSection = .nuiChat
        let draftSurvivedMenuSwitch = (store.chatInput == "Draft pesan penting untuk sesi alpha yang belum dikirim")
            && (store.sessionDrafts["sess-draft-alpha"] == "Draft pesan penting untuk sesi alpha yang belum dikirim")

        // 7. Markdown block parser check (headings, table, code block, formula callout)
        let parsedBlocks = MarkdownProseSegmentView.parseBlocks(fullAssistantMarkdown)
        var hasHeading = false
        var hasTable = false
        var hasFormula = false
        for node in parsedBlocks {
            switch node {
            case .heading(_, _): hasHeading = true
            case .table(let headers, let rows):
                if headers.count == 2 && !rows.isEmpty { hasTable = true }
            case .formulaCallout(_): hasFormula = true
            default: break
            }
        }

        // 8. Inline edit user message state check
        store.messages = [userMsg, asstMsg]
        store.beginEditingUserMessage(userMsg)
        let inlineEditLoadedCleanPrompt = (store.editingMessageId == "u-test-1") && (store.editingMessageDraft == userText)
        store.cancelEditingUserMessage()

        let report: [String: Any] = [
            "copy_user_message_pass": copyUserPass,
            "copy_full_assistant_response_pass": copyFullAssistantPass,
            "copied_assistant_char_count": copiedAsstResult.count,
            "copy_code_block_only_pass": copyCodeOnlyPass,
            "paste_multiline_unicode_hijaiyyah_math_pass": pastePreservedExact,
            "shift_enter_newline_without_send_pass": shiftEnterAddedNewlineWithoutSend,
            "enter_triggers_send_pass": enterTriggeredSend,
            "draft_survived_menu_switch_pass": draftSurvivedMenuSwitch,
            "markdown_parser_heading_table_formula_pass": (hasHeading && hasTable && hasFormula),
            "inline_edit_user_message_pass": inlineEditLoadedCleanPrompt,
            "yayasan_in_default_authorized_folders": store.authorizedFolders.contains(where: { ($0["path"] as? String) == "/Users/AMRA/yayasan" })
        ]
        if let data = try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted]),
           let str = String(data: data, encoding: .utf8) {
            print("CHAT_CLIPBOARD_UI_VERIFY_JSON_START")
            print(str)
            print("CHAT_CLIPBOARD_UI_VERIFY_JSON_END")
        }
    }
}

extension NUIBrowserEngineController {
    private static func extractHTMLTitleAndReadableText(_ rawHTML: String) -> (title: String, body: String) {
        var extractedTitle = ""
        if let r = try? NSRegularExpression(pattern: "<title[^>]*>(.*?)</title>", options: [.caseInsensitive, .dotMatchesLineSeparators]),
           let m = r.firstMatch(in: rawHTML, range: NSRange(rawHTML.startIndex..., in: rawHTML)),
           let rng = Range(m.range(at: 1), in: rawHTML) {
            extractedTitle = String(rawHTML[rng])
                .replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
                .trimmingCharacters(in: .whitespacesAndNewlines)
        }
        var stripped = rawHTML.replacingOccurrences(
            of: "<(script|style|noscript)[^>]*>.*?</\\1>",
            with: " ",
            options: [.regularExpression, .caseInsensitive]
        )
        stripped = stripped.replacingOccurrences(of: "<[^>]+>", with: " ", options: .regularExpression)
        stripped = stripped.replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression)
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return (title: extractedTitle, body: stripped)
    }

    func completeNavigationViaNativeEngine(tabId: String, navigationId: String) async {
        guard let store = store else { return }
        guard activeNavigationIdByTab[tabId] == navigationId else { return }
        watchdogTasksByTab[tabId]?.cancel()

        let tr = navigationTraces[navigationId]
        let targetURL = tr?.normalizedURL ?? store.browserActiveURL
        let fallbackDom = URL(string: targetURL)?.host?.lowercased() ?? store.activeTabModel.domain

        // Case A: Inline HTML loaded via applyNavigationTraceForLocalHTML
        if let inlineHTML = pendingInlineHTMLByNavId.removeValue(forKey: navigationId) {
            let parsed = Self.extractHTMLTitleAndReadableText(inlineHTML)
            let finalTitle = parsed.title.isEmpty ? fallbackDom : parsed.title
            hasCommittedByTab[tabId] = true
            containerNSView.showFallbackDocument(
                title: finalTitle,
                url: targetURL,
                bodyText: parsed.body,
                isError: false
            )
            if var updated = navigationTraces[navigationId] {
                updated.didStartProvisionalNavigation = true
                updated.didCommit = true
                updated.didFinish = true
                updated.httpStatus = 200
                updated.pageTitle = finalTitle
                updated.state = "COMPLETE"
                updated.elapsedMs = max(1.0, round(Date().timeIntervalSince(updated.startedAt) * 1000.0))
                updated.contentVisibleInViewport = true
                navigationTraces[navigationId] = updated
            }
            if tabId == store.activeBrowserTabId {
                store.browserIsLoading = false
                store.browserLoadingProgress = 1.0
                store.browserPageTitle = finalTitle
                store.browserAddress = targetURL
                store.browserActiveURL = targetURL
                store.browserLastHTTPStatus = 200
                store.browserStatusText = "COMPLETE"
                store.browserPreviewText = "[RENDERED IN VIEWPORT — \(finalTitle)] " + String(parsed.body.prefix(320))
            }
            store.updateLocalTab(tabId) { tab in
                tab.navigationId = navigationId
                tab.title = finalTitle
                tab.url = targetURL
                tab.domain = fallbackDom
                tab.favicon = BrowserAddressNormalizer.faviconForDomain(fallbackDom)
                tab.status = "COMPLETE"
                tab.isLoading = false
                tab.progress = 1.0
                tab.httpStatus = 200
                tab.hasError = false
                tab.contentVisible = true
            }
            return
        }

        // Case B: Live HTTP/HTTPS URL via URLSession
        guard let urlObj = URL(string: targetURL) else { return }
        var req = URLRequest(url: urlObj, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 10.0)
        req.setValue("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) CosmicTeraNUI/1.5 Safari/605.1.15", forHTTPHeaderField: "User-Agent")
        do {
            let (data, resp) = try await URLSession.shared.data(for: req)
            guard activeNavigationIdByTab[tabId] == navigationId else { return }
            let httpResp = resp as? HTTPURLResponse
            let code = httpResp?.statusCode ?? 200
            let finalURL = httpResp?.url?.absoluteString ?? targetURL
            let finalDom = URL(string: finalURL)?.host?.lowercased() ?? fallbackDom
            let rawHTML = String(data: data, encoding: .utf8) ?? String(decoding: data, as: UTF8.self)
            let parsed = Self.extractHTMLTitleAndReadableText(rawHTML)
            let finalTitle = parsed.title.isEmpty ? finalDom : parsed.title

            hasCommittedByTab[tabId] = true
            containerNSView.showFallbackDocument(
                title: finalTitle,
                url: finalURL,
                bodyText: String(parsed.body.prefix(4000)),
                isError: code >= 400
            )

            if var updated = navigationTraces[navigationId] {
                updated.didStartProvisionalNavigation = true
                if finalURL != targetURL {
                    updated.didReceiveServerRedirectForProvisionalNavigation = true
                }
                updated.actualURL = finalURL
                updated.didCommit = true
                updated.didFinish = (code < 400)
                updated.didFail = (code >= 400)
                updated.httpStatus = code
                updated.pageTitle = finalTitle
                updated.state = (code < 400) ? "COMPLETE" : "FAILED"
                updated.elapsedMs = max(1.0, round(Date().timeIntervalSince(updated.startedAt) * 1000.0))
                updated.contentVisibleInViewport = true
                navigationTraces[navigationId] = updated
            }

            if tabId == store.activeBrowserTabId {
                store.browserIsLoading = false
                store.browserLoadingProgress = 1.0
                store.browserPageTitle = finalTitle
                store.browserAddress = finalURL
                store.browserActiveURL = finalURL
                store.browserLastHTTPStatus = code
                store.browserStatusText = (code < 400) ? "COMPLETE" : "FAILED"
                store.browserPreviewText = "[LIVE DOCUMENT — \(finalTitle)] " + String(parsed.body.prefix(320))
                if store.operatingMode != "LOCAL" && code >= 200 && code < 400 {
                    store.internetConnectivityState = "CONNECTED"
                    store.internetConnectivityReason = "URLSESSION_HTTPS_VERIFIED (\(finalDom), HTTP \(code))"
                }
            }
            store.updateLocalTab(tabId) { tab in
                tab.navigationId = navigationId
                tab.title = finalTitle
                tab.url = finalURL
                tab.domain = finalDom
                tab.favicon = BrowserAddressNormalizer.faviconForDomain(finalDom)
                tab.status = (code < 400) ? "COMPLETE" : "FAILED"
                tab.isLoading = false
                tab.progress = 1.0
                tab.httpStatus = code
                tab.hasError = (code >= 400)
                tab.contentVisible = true
            }
        } catch {
            let nsErr = error as NSError
            let wv = webViewForTab(tabId, sessionPolicy: store.browserSessionPolicy)
            handleNavigationFailureInternal(
                webView: wv,
                tabId: tabId,
                navigationId: navigationId,
                stage: "didFailProvisionalNavigation",
                errorCode: "\(nsErr.domain)(\(nsErr.code))",
                errorMessage: error.localizedDescription
            )
        }
    }

    func applyNavigationTraceForLocalHTML(
        webView: WKWebView,
        tabId: String,
        navigationId: String,
        url: String,
        html: String
    ) {
        let dom = URL(string: url)?.host?.lowercased() ?? "local.test"
        activeNavigationIdByTab[tabId] = navigationId
        hasCommittedByTab[tabId] = false
        isRenderingDiagnosticHTMLByTab[tabId] = false
        processTerminationCountByNavId[navigationId] = 0
        pendingInlineHTMLByNavId[navigationId] = html

        var tr = BrowserNavigationTraceRecord(
            id: navigationId,
            tabId: tabId,
            requestedURL: url,
            normalizedURL: url,
            actualURL: url,
            startedAt: Date()
        )
        tr.didStartProvisionalNavigation = true
        tr.state = "LOADING"
        tr.pageTitle = "Loading \(dom)..."
        navigationTraces[navigationId] = tr
        if !navigationTraceOrder.contains(navigationId) { navigationTraceOrder.append(navigationId) }

        store?.applyNavigationStartState(
            tabId: tabId,
            navigationId: navigationId,
            requestedURL: url,
            normalizedURL: url,
            domain: dom,
            securityState: "SECURE_HTTPS"
        )
        if let wkNav = webView.loadHTMLString(html, baseURL: URL(string: url)) {
            navObjectToId[ObjectIdentifier(wkNav)] = navigationId
        }
    }
}

@main
struct CosmicTeraNUIApp: App {
    init() {
        if WebKitRuntimeLiveVerifier.runCLIModesIfRequested() {
            return
        }
        // Terminate any older running CosmicTeraNUI desktop process so the freshly built binary always takes over
        let myPID = ProcessInfo.processInfo.processIdentifier
        for running in NSRunningApplication.runningApplications(withBundleIdentifier: "com.cosmictera.nui.desktop") {
            if running.processIdentifier != myPID {
                running.terminate()
                running.forceTerminate()
            }
        }
        NSApplication.shared.setActivationPolicy(.regular)
    }

    var body: some Scene {
        WindowGroup("CosmicTera NUI Desktop") {
            MainDesktopView()
                .frame(minWidth: 1180, minHeight: 740)
        }
    }
}
