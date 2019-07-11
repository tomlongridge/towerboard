<?php

namespace App;

use Illuminate\Database\Eloquent\Model;

class NoticeMessage extends Model
{
    protected $guarded = ['id'];

    public function notice()
    {
        return $this->belongsTo(Notice::class);
    }

    public function createdBy()
    {
        return $this->belongsTo(User::class, 'created_by');
    }
}
