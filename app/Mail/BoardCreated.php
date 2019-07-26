<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;
use App\Board;

class BoardCreated extends Mailable
{
    use Queueable, SerializesModels;

    private $board;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct(Board $board)
    {
        $this->board = $board;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return $this->markdown('mail.boards.created', ['board' => $this->board])
            ->subject($this->board->readable_name . " Board Created");
    }
}
