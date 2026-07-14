def capitalize:
	(.[:1] | ascii_upcase) + .[1:];

map(select(.version != null) |
	{
		version,
		timestamp,
		message,
		commit_id,
		commits: [ .commits[] | select(.merge_commit == false) |
					{
						id,
						message: .message | capitalize,
						group,
						scope,
						raw_message
					}
			]
        }
) | first
