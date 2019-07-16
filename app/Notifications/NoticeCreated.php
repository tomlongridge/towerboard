<?php

namespace App\Notifications;

use App\Notice;
use App\User;

use Illuminate\Bus\Queueable;
use Illuminate\Notifications\Notification;
use Illuminate\Contracts\Queue\ShouldQueue;

class NoticeCreated extends Notification implements ShouldQueue
{
    use Queueable;

    private $notice;

    /**
     * Create a new notification instance.
     *
     * @return void
     */
    public function __construct(Notice $notice)
    {
        $this->notice = $notice;
    }

    /**
     * Get the notification's delivery channels.
     *
     * @param  mixed  $notifiable
     * @return array
     */
    public function via(User $user)
    {
        return ['mail'];
    }

    /**
     * Get the mail representation of the notification.
     *
     * @param  mixed  $notifiable
     * @return \Illuminate\Notifications\Messages\MailMessage
     */
    public function toMail(User $user)
    {
        return (new \App\Mail\NoticeCreated($this->notice))->to($user->email);
    }

    /**
     * Get the array representation of the notification.
     *
     * @param  mixed  $notifiable
     * @return array
     */
    public function toArray(User $user)
    {
        return [
            //
        ];
    }
}
