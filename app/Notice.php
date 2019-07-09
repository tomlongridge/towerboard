<?php

namespace App;

use BenSampo\Enum\Traits\CastsEnums;
use Carbon\Carbon;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Illuminate\Support\Facades\Notification;

use App\Notifications\NoticeCreated;


use App\Enums\SubscriptionType;

class Notice extends Model
{
    use CastsEnums;
    protected $enumCasts = [
        'distribution' => SubscriptionType::class
    ];

    use SoftDeletes;
    protected $guarded = ['id'];

    protected static function boot()
    {
        parent::boot();

        static::created(function ($notice) {
            $notice->load('createdBy');
            Notification::send(
                $notice->board->subscribers()->wherePivot('type', '>=', $notice->distribution->value)->get(),
                new NoticeCreated($notice)
            );
        });
    }

    public function board()
    {
        return $this->belongsTo(Board::class);
    }

    public function createdBy()
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function replyTo()
    {
        return $this->belongsTo(User::class, 'reply_to');
    }

    public function getExpiresAttribute($expires)
    {
        return $expires != null ? new Carbon($expires) : null;
    }

    public function getExpiredAttribute()
    {
        return $this->expires != null && $this->expires->isPast();
    }
}
