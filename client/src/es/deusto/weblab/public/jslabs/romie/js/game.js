Game = function(time)
{
	this.points = 0;
	this.time = time;
	this.topCamTimmer = null;
	this.timer = null;
	this.topCamTime = 0;

	this.startGame();
}

Game.prototype.startGame = function()
{
	this.timer = setInterval(function() {

		this.time -= 0.01;
		$('.time span').html(Math.floor(this.time/60) + ":" + (Math.floor((this.time%60) * 100) / 100));
		if (this.time <= 0)
		{
			this.time = 0;
			$('.time span').html("0:00.00");

			this.endGame();
		}

		}.bind(this), 10);
}

Game.prototype.endGame = function()
{
	clearInterval(this.timer);
	$('#game_end_points').text(this.points);

	// TODO show records

	$('#game_end').modal('show');
}

Game.prototype.showQuestion = function(question)
{
	console.log(question);
	question = JSON.parse(question);

	$('#questionLabel').html(question["question"]);

	i = 0;
	question["answers"].forEach(function(answer)
	{
		$('#question .modal-body form')
			.append('<input type="radio" name="answer" id="ans_'+i+'" value="'+i+'">'+
				'<label for="ans_'+i+'">'+answer+'</label><br>');
		i++;
	}.bind(i));
	$("#question").modal({keyboard:false});

	this.question = question;
}

Game.prototype.answerQuestion = function()
{
	answer = parseInt($('#question input[name="answer"]:checked').val());

	if ( ! isNaN(answer))
	{
		$("#question").modal('hide');

		Weblab.sendCommand("ANSWER "+answer+" "+this.question["difficulty"]+" "+
			this.question["index"]+" "+this.question["category"], function(response)
			{
				if (response == 'True')
				{
					this.points += this.question["points"];
					this.time += this.question["time"];

					$('.points span').html(this.points);
					this.topCamTime += 10;
					$('#response_ok').modal('show');
				}
				else
				{
					$('#response_wrong').modal('show');
				}

				this.question = {};
				$('#questionLabel').html("");
				$('#question .modal-body form').html("");
			}.bind(this));
	}
}

Game.prototype.getQuestion = function(tag)
{
	// TODO better difficulty check and more categories
	difficulty = Math.floor(this.points/500);
	category = "general";

	Weblab.sendCommand("QUESTION "+difficulty+" "+category, function(response){this.showQuestion(response);}.bind(this));
}

Game.prototype.getTopCamTime = function()
{
	return this.topCamTime;
}

Game.prototype.isTopCamActive = function()
{
	return this.topCamActive;
}

Game.prototype.deactivateTopCam = function()
{
	this.topCamActive = false;
}

Game.prototype.activateTopCam = function()
{
	this.topCamActive = true;

	this.topCamTimer = setInterval(function()
	{
		if (this.topCamActive)
			this.topCamTime--;
		else
			this.deactivateTopCam();
	}.bind(this), 1000);
}

Game.prototype.getPoints = function()
{
	return this.points;
}
