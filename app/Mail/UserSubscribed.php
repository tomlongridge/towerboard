<?php

namespace App\Mail;

use App\Board;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;
use Illuminate\Contracts\Queue\ShouldQueue;
use App\User;

class UserSubscribed extends Mailable
{
    use Queueable, SerializesModels;

    private $board;
    private $user;
    private $addedBy;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct(Board $board, User $user, User $addedBy)
    {
        $this->board = $board;
        $this->user = $user;
        $this->addedBy = $addedBy;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return
            $this->markdown(
                'mail.boards.usersubscribed',
                [
                    'board' => $this->board,
                    'user' => $this->user,
                    'addedBy' => $this->addedBy,
                ]
            )
            ->subject("Welcome to the {$this->board->readable_name} Towerboard")
            ->from($this->addedBy->email, $this->addedBy->name);
    }
}
