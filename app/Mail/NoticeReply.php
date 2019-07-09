<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;
use Illuminate\Contracts\Queue\ShouldQueue;

class NoticeReply extends Mailable
{
    use Queueable, SerializesModels;

    private $notice;
    private $sentFrom;
    private $message;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct($notice, $sentFrom, $message)
    {
        $this->notice = $notice;
        $this->sentFrom = $sentFrom;
        $this->message = $message;
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
                'mail.notices.reply',
                [
                    'notice' => $this->notice,
                    'sentFrom' => $this->sentFrom,
                    'message' => $this->message,
                ]
            )
            ->subject("RE: {$this->notice->title}")
            ->from($this->sentFrom->email, $this->sentFrom->name);
    }
}
