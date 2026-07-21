. | {
	version: .version | ltrimstr("v"),
	release_date: .timestamp | todateiso8601,
	description: .message,
	commit_id,
	sections: (
		.commits
		| group_by(.scope)
		| map({
			name: .[0].scope,
			features: map(select(.group == "features") | { id, message }),
			fixes: map(select(.group == "fixes") | { id, message })
		      })
	)
}
