<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Mail\Mailable;
use Illuminate\Queue\SerializesModels;
use App\Board;
use App\User;
use Carbon\Carbon;

class BoardContactMessage extends Mailable
{
    use Queueable, SerializesModels;

    private $board;
    private $sentFrom;
    private $messageBody;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct(Board $board, User $sentFrom, string $messageBody)
    {
        $this->board = $board;
        $this->sentFrom = $sentFrom;
        $this->messageBody = $messageBody;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return $this->markdown('mail.boards.contact', [
                  'board' => $this->board,
                  'messageBody' => $this->messageBody,
                  'sentFrom' => $this->sentFrom,
                  'sentAt' => Carbon::now()
               ])
               ->subject('Contact Form message for ' . $this->board->readableName)
               ->from($this->sentFrom->email, $this->sentFrom->name);
    }
}
