<?php

namespace App\Mail;

use App\Notice;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Queue\SerializesModels;

class NoticeUpdated extends Mailable
{
    use Queueable, SerializesModels;

    private $notice;

    /**
     * Create a new message instance.
     *
     * @return void
     */
    public function __construct(Notice $notice)
    {
        $this->notice = $notice;
    }

    /**
     * Build the message.
     *
     * @return $this
     */
    public function build()
    {
        return $this->markdown('mail.notices.updated', ['notice' => $this->notice])
            ->subject('Updated: ' . $this->notice->title)
            ->from(
                $this->notice->createdBy()->first()->email,
                $this->notice->createdBy()->first()->name
            );
    }
}
