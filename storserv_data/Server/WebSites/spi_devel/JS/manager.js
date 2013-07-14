var section_location = '';

function init_manager( location )
{
	section_location = location;

	var authors = [];
	var users = [];

	$.get("/Scripts/get_section?loc=" + location, function(author_data) {
		authors = json_parse(author_data).Author;

		$.get("/Scripts/get_users", function(user_data) {
			users = user_data.split(',');

			for (var i=0; i<authors.length; i++)
			{
				for (var j=0; j<users.length; j++)
				{
					if (users[j] == authors[i])
					{
						users.splice(j,j);
					}
				}
			}

			for (var i=1; i<authors.length; i++) //Counter starts at one. Owner is index 0
			{
				$('#authors').append( new Option(authors[i], authors[i]) );
			}

			for (var i=0; i<users.length; i++)
			{
				$('#users').append( new Option(users[i], users[i]) );
			}
		});
	});
}

function add_user()
{
	$('#authors').append( $('#users').get(0).children[ $('#users').get(0).selectedIndex ] );
}

function remove_user()
{
	$('#users').append( $('#authors').get(0).children[ $('#authors').get(0).selectedIndex ] );
}

function submit_authors()
{
	var authors = [];

	$('#authors').children().map( function() {
		authors.push( this.value );
	});

	var plainPostDataObject = {};
	plainPostDataObject.loc = section_location;
	plainPostDataObject.data = JSON.stringify(authors);

	$.post("/Scripts/manage_section", plainPostDataObject, function() {
		window.location.href = "/Editor/edit_section?loc=" + section_location;
	}); 
}
