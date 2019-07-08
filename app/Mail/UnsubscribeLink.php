<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;
use Illuminate\Contracts\Queue\ShouldQueue;

class UnsubscribeLink extends Mailable
{
    use Queueable, SerializesModels;

    private $board;
    private $unsubscribeLink;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct($board, $unsubscribeLink)
    {
        $this->board = $board;
        $this->unsubscribeLink = $unsubscribeLink;
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
              'mail.boards.unsubscribelink',
              [
                  'board' => $this->board,
                  'unsubscribeLink' => $this->unsubscribeLink,
              ]
          )
          ->subject("Unsubscribe from {$this->board->readable_name} on Towerboard");
    }
}
