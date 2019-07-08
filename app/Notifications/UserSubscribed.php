<?php

namespace App\Notifications;

use App\Notice;
use App\User;

use Illuminate\Bus\Queueable;
use Illuminate\Notifications\Notification;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Notifications\Messages\MailMessage;
use App\Board;

class UserSubscribed extends Notification
{
    use Queueable;

    private $board;
    private $user;
    private $addedBy;

    /**
     * Create a new notification instance.
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
        return (new \App\Mail\UserSubscribed($this->board, $this->user, $this->addedBy))->to($user->email);
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
