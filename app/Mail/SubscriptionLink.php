<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;

class SubscriptionLink extends Mailable
{
    use Queueable, SerializesModels;

    private $board;
    private $link;
    private $subscribe;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct($board, $link, $subscribe)
    {
        $this->board = $board;
        $this->link = $link;
        $this->subscribe = $subscribe;
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
              'mail.boards.subscription-link',
              [
                  'board' => $this->board,
                  'link' => $this->link,
                  'subscribe' => $this->subscribe,
              ]
          )
          ->subject(($this->subscribe ? "Subscribe to" : "Unsubscribe from") .
                    " {$this->board->readable_name} on " . config('app.name'));
    }
}
