import Foundation
import IssueTrackerClient

// Tiny command line front end:
//   issuetracker-cli login <user> <password>      (prints a token)
//   issuetracker-cli list [text]
//   issuetracker-cli show <id>
//   issuetracker-cli create <title> <component> [P1-P4]
// Environment: TRACKER_URL (default http://127.0.0.1:8000/api), TRACKER_TOKEN

func fail(_ message: String) -> Never {
    FileHandle.standardError.write(Data((message + "\n").utf8))
    exit(1)
}

let environment = ProcessInfo.processInfo.environment
guard let baseURL = URL(string: environment["TRACKER_URL"] ?? "http://127.0.0.1:8000/api") else {
    fail("TRACKER_URL is not a valid URL")
}
let client = IssueTrackerClient(baseURL: baseURL, token: environment["TRACKER_TOKEN"])
let arguments = Array(CommandLine.arguments.dropFirst())

func describe(_ issue: Issue) -> String {
    "#\(issue.id) [\(issue.priority.rawValue)] \(issue.state.rawValue) - \(issue.title) (\(issue.component))"
}

func run() async throws {
    switch arguments.first {
    case "login" where arguments.count == 3:
        print(try await client.login(username: arguments[1], password: arguments[2]))
    case "list":
        let issues = try await client.listIssues(text: arguments.count > 1 ? arguments[1] : nil)
        issues.forEach { print(describe($0)) }
    case "show" where arguments.count == 2:
        guard let id = Int(arguments[1]) else { fail("id must be a number") }
        print(describe(try await client.getIssue(id: id)))
    case "create" where arguments.count >= 3:
        let priority = arguments.count > 3 ? Priority(rawValue: arguments[3]) : .p3
        guard let chosen = priority else { fail("priority must be P1, P2, P3 or P4") }
        let created = try await client.createIssue(
            NewIssue(title: arguments[1], component: arguments[2], priority: chosen))
        print("Created " + describe(created))
    default:
        fail("usage: issuetracker-cli login <user> <password> | list [text] | show <id> | create <title> <component> [P1-P4]")
    }
}

do {
    try await run()
} catch {
    fail("Error: \(error)")
}
