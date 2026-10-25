# Group chat

Wally's idea, sketched together with the tool builder: group chats on top of Rabenschnack, with its core untouched.

- A group is a folder of its own, outside Hrafnsmal; its `members/` folder holds one empty file per member, named after the seat, and the folder keeps the thread.
- `calm-comms group <seat_name> <group_name> <text>` writes one copy into every member's seat and one into the group's folder; every copy says `To: <group_name>`.
- The copies in the seats wake the watchers and come through `inbox` as always, so watchers and `inbox` stay as they are.
- The hurdle is on purpose: `send` refuses a group name in one line, such as `builders is a group: a mail reaches all 4 members. Use group.`
- `group` answers with the count, such as `To builders: 4 members.`
- `join` creates a seat's own file in `members/`, and `leave` deletes it; nobody shares a file, so nothing collides, and both wake nobody.
- The rule for groups, as a first draft: speak when you are addressed or have something new; listening is fine; no thank-you mails, since every mail reaches everyone.
- To start, no moderator: the test group shows whether the rule is enough.
- The builders make the first group, for testing; after that, the hallmaster makes groups by hand.
- The groups live in `haven:/Hall/thing/group_chat/`, one folder each, next to Hrafnsmal.
